<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()> _
Partial Class FrmPrincipal
    Inherits System.Windows.Forms.Form

    'Form overrides dispose to clean up the component list.
    <System.Diagnostics.DebuggerNonUserCode()> _
    Protected Overrides Sub Dispose(ByVal disposing As Boolean)
        Try
            If disposing AndAlso components IsNot Nothing Then
                components.Dispose()
            End If
        Finally
            MyBase.Dispose(disposing)
        End Try
    End Sub

    'Required by the Windows Form Designer
    Private components As System.ComponentModel.IContainer

    'NOTE: The following procedure is required by the Windows Form Designer
    'It can be modified using the Windows Form Designer.  
    'Do not modify it using the code editor.
    <System.Diagnostics.DebuggerStepThrough()> _
    Private Sub InitializeComponent()
        Me.components = New System.ComponentModel.Container()
        Dim resources As System.ComponentModel.ComponentResourceManager = New System.ComponentModel.ComponentResourceManager(GetType(FrmPrincipal))
        Me.MenuStrip1 = New System.Windows.Forms.MenuStrip()
        Me.MenuToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.CerrarToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.EgresosToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.ComprasToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.GeneralesToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.AgregarRegistrosToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.VerRegistrosToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.InformesToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.HaciendaToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.ComprasHaciendaToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.ImpuestosToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.IngresosToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.GanaderiaToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.VentasDirectasToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.VentasFeriaToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.AgriculturaToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.VentasGranosToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.ArrendamientosToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.BancosToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.ValoresToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.TarjetasToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.ResumenesToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.VentanaToolStripMenuItem = New System.Windows.Forms.ToolStripMenuItem()
        Me.ContextMenuStrip1 = New System.Windows.Forms.ContextMenuStrip(Me.components)
        Me.ContextMenuStrip2 = New System.Windows.Forms.ContextMenuStrip(Me.components)
        Me.MenuStrip1.SuspendLayout()
        Me.SuspendLayout()
        '
        'MenuStrip1
        '
        Me.MenuStrip1.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.MenuStrip1.Items.AddRange(New System.Windows.Forms.ToolStripItem() {Me.MenuToolStripMenuItem, Me.EgresosToolStripMenuItem, Me.IngresosToolStripMenuItem, Me.BancosToolStripMenuItem, Me.VentanaToolStripMenuItem})
        Me.MenuStrip1.Location = New System.Drawing.Point(0, 0)
        Me.MenuStrip1.MdiWindowListItem = Me.BancosToolStripMenuItem
        Me.MenuStrip1.Name = "MenuStrip1"
        Me.MenuStrip1.Size = New System.Drawing.Size(677, 24)
        Me.MenuStrip1.TabIndex = 0
        Me.MenuStrip1.Text = "PrincipalMenuStrip"
        '
        'MenuToolStripMenuItem
        '
        Me.MenuToolStripMenuItem.DropDownItems.AddRange(New System.Windows.Forms.ToolStripItem() {Me.CerrarToolStripMenuItem})
        Me.MenuToolStripMenuItem.Name = "MenuToolStripMenuItem"
        Me.MenuToolStripMenuItem.Size = New System.Drawing.Size(68, 20)
        Me.MenuToolStripMenuItem.Text = "&Archivo"
        '
        'CerrarToolStripMenuItem
        '
        Me.CerrarToolStripMenuItem.Name = "CerrarToolStripMenuItem"
        Me.CerrarToolStripMenuItem.Size = New System.Drawing.Size(116, 22)
        Me.CerrarToolStripMenuItem.Text = "Cerrar"
        '
        'EgresosToolStripMenuItem
        '
        Me.EgresosToolStripMenuItem.DropDownItems.AddRange(New System.Windows.Forms.ToolStripItem() {Me.ComprasToolStripMenuItem, Me.ComprasHaciendaToolStripMenuItem, Me.ImpuestosToolStripMenuItem})
        Me.EgresosToolStripMenuItem.Name = "EgresosToolStripMenuItem"
        Me.EgresosToolStripMenuItem.Size = New System.Drawing.Size(68, 20)
        Me.EgresosToolStripMenuItem.Text = "Egresos"
        '
        'ComprasToolStripMenuItem
        '
        Me.ComprasToolStripMenuItem.DropDownItems.AddRange(New System.Windows.Forms.ToolStripItem() {Me.GeneralesToolStripMenuItem, Me.HaciendaToolStripMenuItem})
        Me.ComprasToolStripMenuItem.Name = "ComprasToolStripMenuItem"
        Me.ComprasToolStripMenuItem.Size = New System.Drawing.Size(172, 22)
        Me.ComprasToolStripMenuItem.Text = "Compras"
        '
        'GeneralesToolStripMenuItem
        '
        Me.GeneralesToolStripMenuItem.DropDownItems.AddRange(New System.Windows.Forms.ToolStripItem() {Me.AgregarRegistrosToolStripMenuItem, Me.VerRegistrosToolStripMenuItem, Me.InformesToolStripMenuItem})
        Me.GeneralesToolStripMenuItem.Name = "GeneralesToolStripMenuItem"
        Me.GeneralesToolStripMenuItem.Size = New System.Drawing.Size(137, 22)
        Me.GeneralesToolStripMenuItem.Text = "Generales"
        '
        'AgregarRegistrosToolStripMenuItem
        '
        Me.AgregarRegistrosToolStripMenuItem.DisplayStyle = System.Windows.Forms.ToolStripItemDisplayStyle.Text
        Me.AgregarRegistrosToolStripMenuItem.ImageScaling = System.Windows.Forms.ToolStripItemImageScaling.None
        Me.AgregarRegistrosToolStripMenuItem.Name = "AgregarRegistrosToolStripMenuItem"
        Me.AgregarRegistrosToolStripMenuItem.Size = New System.Drawing.Size(193, 22)
        Me.AgregarRegistrosToolStripMenuItem.Text = "Agregar Registros"
        '
        'VerRegistrosToolStripMenuItem
        '
        Me.VerRegistrosToolStripMenuItem.Name = "VerRegistrosToolStripMenuItem"
        Me.VerRegistrosToolStripMenuItem.Size = New System.Drawing.Size(193, 22)
        Me.VerRegistrosToolStripMenuItem.Text = "Ver Registros"
        '
        'InformesToolStripMenuItem
        '
        Me.InformesToolStripMenuItem.Name = "InformesToolStripMenuItem"
        Me.InformesToolStripMenuItem.Size = New System.Drawing.Size(193, 22)
        Me.InformesToolStripMenuItem.Text = "Informes"
        '
        'HaciendaToolStripMenuItem
        '
        Me.HaciendaToolStripMenuItem.Name = "HaciendaToolStripMenuItem"
        Me.HaciendaToolStripMenuItem.Size = New System.Drawing.Size(137, 22)
        Me.HaciendaToolStripMenuItem.Text = "Hacienda"
        '
        'ComprasHaciendaToolStripMenuItem
        '
        Me.ComprasHaciendaToolStripMenuItem.Name = "ComprasHaciendaToolStripMenuItem"
        Me.ComprasHaciendaToolStripMenuItem.Size = New System.Drawing.Size(172, 22)
        Me.ComprasHaciendaToolStripMenuItem.Text = "Remuneraciones"
        '
        'ImpuestosToolStripMenuItem
        '
        Me.ImpuestosToolStripMenuItem.Name = "ImpuestosToolStripMenuItem"
        Me.ImpuestosToolStripMenuItem.Size = New System.Drawing.Size(172, 22)
        Me.ImpuestosToolStripMenuItem.Text = "Impuestos"
        '
        'IngresosToolStripMenuItem
        '
        Me.IngresosToolStripMenuItem.DropDownItems.AddRange(New System.Windows.Forms.ToolStripItem() {Me.GanaderiaToolStripMenuItem, Me.AgriculturaToolStripMenuItem, Me.ArrendamientosToolStripMenuItem})
        Me.IngresosToolStripMenuItem.Name = "IngresosToolStripMenuItem"
        Me.IngresosToolStripMenuItem.Size = New System.Drawing.Size(75, 20)
        Me.IngresosToolStripMenuItem.Text = "Ingresos"
        '
        'GanaderiaToolStripMenuItem
        '
        Me.GanaderiaToolStripMenuItem.DropDownItems.AddRange(New System.Windows.Forms.ToolStripItem() {Me.VentasDirectasToolStripMenuItem, Me.VentasFeriaToolStripMenuItem})
        Me.GanaderiaToolStripMenuItem.Name = "GanaderiaToolStripMenuItem"
        Me.GanaderiaToolStripMenuItem.Size = New System.Drawing.Size(172, 22)
        Me.GanaderiaToolStripMenuItem.Text = "Ganaderia"
        '
        'VentasDirectasToolStripMenuItem
        '
        Me.VentasDirectasToolStripMenuItem.Name = "VentasDirectasToolStripMenuItem"
        Me.VentasDirectasToolStripMenuItem.Size = New System.Drawing.Size(179, 22)
        Me.VentasDirectasToolStripMenuItem.Text = "Ventas Directas"
        '
        'VentasFeriaToolStripMenuItem
        '
        Me.VentasFeriaToolStripMenuItem.Name = "VentasFeriaToolStripMenuItem"
        Me.VentasFeriaToolStripMenuItem.Size = New System.Drawing.Size(179, 22)
        Me.VentasFeriaToolStripMenuItem.Text = "Ventas Feria"
        '
        'AgriculturaToolStripMenuItem
        '
        Me.AgriculturaToolStripMenuItem.DropDownItems.AddRange(New System.Windows.Forms.ToolStripItem() {Me.VentasGranosToolStripMenuItem})
        Me.AgriculturaToolStripMenuItem.Name = "AgriculturaToolStripMenuItem"
        Me.AgriculturaToolStripMenuItem.Size = New System.Drawing.Size(172, 22)
        Me.AgriculturaToolStripMenuItem.Text = "Agricultura"
        '
        'VentasGranosToolStripMenuItem
        '
        Me.VentasGranosToolStripMenuItem.Name = "VentasGranosToolStripMenuItem"
        Me.VentasGranosToolStripMenuItem.Size = New System.Drawing.Size(165, 22)
        Me.VentasGranosToolStripMenuItem.Text = "Ventas Granos"
        '
        'ArrendamientosToolStripMenuItem
        '
        Me.ArrendamientosToolStripMenuItem.Name = "ArrendamientosToolStripMenuItem"
        Me.ArrendamientosToolStripMenuItem.Size = New System.Drawing.Size(172, 22)
        Me.ArrendamientosToolStripMenuItem.Text = "Arrendamientos"
        '
        'BancosToolStripMenuItem
        '
        Me.BancosToolStripMenuItem.DropDownItems.AddRange(New System.Windows.Forms.ToolStripItem() {Me.ValoresToolStripMenuItem, Me.TarjetasToolStripMenuItem, Me.ResumenesToolStripMenuItem})
        Me.BancosToolStripMenuItem.Name = "BancosToolStripMenuItem"
        Me.BancosToolStripMenuItem.Size = New System.Drawing.Size(61, 20)
        Me.BancosToolStripMenuItem.Text = "Bancos"
        '
        'ValoresToolStripMenuItem
        '
        Me.ValoresToolStripMenuItem.Name = "ValoresToolStripMenuItem"
        Me.ValoresToolStripMenuItem.Size = New System.Drawing.Size(137, 22)
        Me.ValoresToolStripMenuItem.Text = "Valores"
        '
        'TarjetasToolStripMenuItem
        '
        Me.TarjetasToolStripMenuItem.Name = "TarjetasToolStripMenuItem"
        Me.TarjetasToolStripMenuItem.Size = New System.Drawing.Size(137, 22)
        Me.TarjetasToolStripMenuItem.Text = "Tarjetas"
        '
        'ResumenesToolStripMenuItem
        '
        Me.ResumenesToolStripMenuItem.Name = "ResumenesToolStripMenuItem"
        Me.ResumenesToolStripMenuItem.Size = New System.Drawing.Size(137, 22)
        Me.ResumenesToolStripMenuItem.Text = "Resumenes"
        '
        'VentanaToolStripMenuItem
        '
        Me.VentanaToolStripMenuItem.Name = "VentanaToolStripMenuItem"
        Me.VentanaToolStripMenuItem.Size = New System.Drawing.Size(68, 20)
        Me.VentanaToolStripMenuItem.Text = "&Ventana"
        '
        'ContextMenuStrip1
        '
        Me.ContextMenuStrip1.Name = "ContextMenuStrip1"
        Me.ContextMenuStrip1.Size = New System.Drawing.Size(61, 4)
        '
        'ContextMenuStrip2
        '
        Me.ContextMenuStrip2.Name = "ContextMenuStrip2"
        Me.ContextMenuStrip2.Size = New System.Drawing.Size(61, 4)
        '
        'FrmPrincipal
        '
        Me.AllowDrop = True
        Me.AutoScaleDimensions = New System.Drawing.SizeF(6.0!, 13.0!)
        Me.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font
        Me.BackColor = System.Drawing.SystemColors.Control
        Me.BackgroundImageLayout = System.Windows.Forms.ImageLayout.None
        Me.ClientSize = New System.Drawing.Size(677, 434)
        Me.Controls.Add(Me.MenuStrip1)
        Me.Font = New System.Drawing.Font("Consolas", 8.25!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.FormBorderStyle = System.Windows.Forms.FormBorderStyle.Fixed3D
        Me.Icon = CType(resources.GetObject("$this.Icon"), System.Drawing.Icon)
        Me.IsMdiContainer = True
        Me.MainMenuStrip = Me.MenuStrip1
        Me.Name = "FrmPrincipal"
        Me.Text = "Sistema La Herencia"
        Me.WindowState = System.Windows.Forms.FormWindowState.Maximized
        Me.MenuStrip1.ResumeLayout(False)
        Me.MenuStrip1.PerformLayout()
        Me.ResumeLayout(False)
        Me.PerformLayout()

    End Sub
    Friend WithEvents MenuStrip1 As System.Windows.Forms.MenuStrip
    Friend WithEvents MenuToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents CerrarToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents EgresosToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents ComprasToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents GeneralesToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents HaciendaToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents ComprasHaciendaToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents IngresosToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents GanaderiaToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents VentasDirectasToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents VentasFeriaToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents AgriculturaToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents VentasGranosToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents BancosToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents ValoresToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents TarjetasToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents ResumenesToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents ImpuestosToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents ArrendamientosToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents VentanaToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents AgregarRegistrosToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents VerRegistrosToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents InformesToolStripMenuItem As System.Windows.Forms.ToolStripMenuItem
    Friend WithEvents ContextMenuStrip1 As System.Windows.Forms.ContextMenuStrip
    Friend WithEvents ContextMenuStrip2 As System.Windows.Forms.ContextMenuStrip

End Class
