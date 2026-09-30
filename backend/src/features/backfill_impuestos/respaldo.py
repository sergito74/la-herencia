"""Evidencia operativa firmada: nunca datos de negocio ni permisos del cliente."""
import base64, hashlib, hmac, json, os, time
from pathlib import Path
from uuid import UUID,uuid4
from src.auth.secret import get_secret
from src.db.connection import get_connection
from .documentos import filehash
from .diagnostico import digest

def directorio():
    p=Path(os.environ.get('LA_HERENCIA_BACKFILL_BACKUPS',r'C:\Temp\LaHerencia029')).resolve()
    repo=Path(__file__).resolve().parents[4]
    if p.is_relative_to(repo): raise ValueError('El backup debe quedar fuera del repositorio')
    return p

def sign(data):
    raw=base64.urlsafe_b64encode(json.dumps(data,sort_keys=True).encode()).decode()
    sig=hmac.new(get_secret(),('029:'+raw).encode(),hashlib.sha256).hexdigest()
    return raw+'.'+sig

def decode(token):
    try:
        raw,sig=token.split('.')
        expected=hmac.new(get_secret(),('029:'+raw).encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig,expected): raise ValueError()
        return json.loads(base64.urlsafe_b64decode(raw))
    except (ValueError,UnicodeError,TypeError) as exc: raise ValueError('Evidencia o preparación inválida') from exc

def preparar(finalidad,huella,usuario):
    return sign(dict(tipo='preparacion',finalidad=finalidad,huella=huella,usuario=str(usuario),fecha=time.time()))

def check_preparacion(token,finalidad,huella,usuario):
    p=decode(token)
    if p.get('tipo')!='preparacion' or p.get('finalidad')!=finalidad or p.get('huella')!=huella or p.get('usuario')!=str(usuario) or not 0<=time.time()-p.get('fecha',0)<=86400:
        raise ValueError('La preparación venció o no corresponde a esta operación y usuario')
    return p

def crear(token):
    p=decode(token)
    check_preparacion(token,p.get('finalidad'),p.get('huella'),p.get('usuario'))
    root=directorio();root.mkdir(parents=True,exist_ok=True)
    key=str(uuid4());path=root/(key+'.bak');started=time.time()
    with get_connection(readonly=False) as conn:
        cur=conn.cursor();cur.execute('SELECT DB_NAME()')
        if cur.fetchone()[0]!='WC': raise ValueError('Base incorrecta')
        cur.execute('BACKUP DATABASE [WC] TO DISK = ? WITH COPY_ONLY, CHECKSUM',(str(path),))
        while cur.nextset(): pass
        cur.execute('RESTORE VERIFYONLY FROM DISK = ? WITH CHECKSUM',(str(path),))
        while cur.nextset(): pass
    evidence=dict(tipo='backup',backupId=key,base='WC',preparacionHash=digest(token),inicio=started,
                  verificadoEn=time.time(),ruta=str(path),archivoHash=filehash(path))
    (root/(key+'.json')).write_text(sign(evidence),encoding='utf-8')
    return evidence

def verificar(key,token):
    key=str(UUID(str(key)));root=directorio();p=decode(token)
    try: data=decode((root/(key+'.json')).read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc: raise ValueError('No existe evidencia válida de backup') from exc
    path=Path(data.get('ruta','')).resolve()
    if data.get('tipo')!='backup' or data.get('backupId')!=key or data.get('base')!='WC' or data.get('preparacionHash')!=digest(token) or data.get('inicio',0)<p.get('fecha',float('inf')) or not path.is_relative_to(root) or not path.is_file() or filehash(path)!=data.get('archivoHash'):
        raise ValueError('El respaldo no corresponde o cambió desde su verificación')
    return data

def estado(token,usuario):
    p=decode(token);check_preparacion(token,p.get('finalidad'),p.get('huella'),usuario)
    root=directorio()
    for f in sorted(root.glob('*.json'),reverse=True):
        try:
            e=decode(f.read_text(encoding='utf-8'))
            if e.get('preparacionHash')!=digest(token): continue
            e=verificar(f.stem,token)
            return dict(estado='verificado',backupId=e['backupId'],verificadoEn=e['verificadoEn'])
        except (ValueError,OSError): continue
    return dict(estado='pendiente',motivo='Prepará el respaldo con la herramienta local y refrescá.')
