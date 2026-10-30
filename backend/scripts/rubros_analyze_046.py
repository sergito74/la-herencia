"""046 (/speckit-analyze 30/10/2026, C1/C2): Gastos Comercializacion deja de retener; Flete granos queda marcado para revisión."""
import json

from src.db.connection import _assert_target_is_wc, execute_write_transaction
from src.features.retenciones_ganancias.repository import OBSERVACIONES
from src.features.vinculos.backup import backup_verificado

if __name__ == '__main__':
    _assert_target_is_wc()
    respaldo = backup_verificado('rubros-analyze-046')
    sql = ("UPDATE dbo.RetencionesGanancias_Conceptos SET {}Observaciones=?,Estado='Borrador',Usuario='Claude046',"
           "Modificado=SYSUTCDATETIME() WHERE IdRubro=(SELECT IdRubro FROM dbo.Rubros WHERE Rubro=?)")
    execute_write_transaction([
        (sql.format('CodRegimen=NULL,'), (OBSERVACIONES['Gastos Comercializacion'], 'Gastos Comercializacion')),
        (sql.format(''), (OBSERVACIONES['Flete granos'], 'Flete granos')),
        ("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
         "VALUES ('rubros-analyze-046','aplicada',?,'Claude046',SYSDATETIME(),'Claude046',SYSDATETIME(),?,?)",
         (json.dumps(OBSERVACIONES, ensure_ascii=False), respaldo,
          'Retenciones 046: Gastos Comercializacion sin retención (granos excluidos); Flete granos marcado para revisión.'))])
    print('Aplicado. Respaldo:', respaldo)
