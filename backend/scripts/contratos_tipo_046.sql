IF COL_LENGTH('dbo.ContratosCanje','Tipo') IS NULL
    ALTER TABLE dbo.ContratosCanje ADD Tipo varchar(10) NOT NULL CONSTRAINT DF_ContratosCanje_Tipo DEFAULT 'canje'
        CONSTRAINT CK_ContratosCanje_Tipo CHECK (Tipo IN ('canje','venta'));
