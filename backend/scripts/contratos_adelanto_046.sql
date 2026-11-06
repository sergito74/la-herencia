IF COL_LENGTH('dbo.ContratosCanje','MedioAdelanto') IS NULL
    ALTER TABLE dbo.ContratosCanje ADD MedioAdelanto varchar(10) NULL, IdMovimientoAdelanto int NULL, Fuente nvarchar(30) NULL;
