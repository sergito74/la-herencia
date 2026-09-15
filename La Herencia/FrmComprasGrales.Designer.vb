<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()> _
Partial Class FrmComprasGrales
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
        Me.DTPFecha = New System.Windows.Forms.DateTimePicker()
        Me.LblFecha = New System.Windows.Forms.Label()
        Me.LblProveedor = New System.Windows.Forms.Label()
        Me.CmbProveedor = New System.Windows.Forms.ComboBox()
        Me.LblLetraDoc = New System.Windows.Forms.Label()
        Me.CmbLetraDoc = New System.Windows.Forms.ComboBox()
        Me.CmbTipoDoc = New System.Windows.Forms.ComboBox()
        Me.LblTipoDoc = New System.Windows.Forms.Label()
        Me.LblNDoc = New System.Windows.Forms.Label()
        Me.TxtNumDoc = New System.Windows.Forms.TextBox()
        Me.DTGVDetCompras = New System.Windows.Forms.DataGridView()
        Me.TxtSubtotal = New System.Windows.Forms.TextBox()
        Me.LblSubtotal = New System.Windows.Forms.Label()
        Me.TxtIVA = New System.Windows.Forms.TextBox()
        Me.LblIVA = New System.Windows.Forms.Label()
        Me.TxtCNoGrav = New System.Windows.Forms.TextBox()
        Me.LblCNoGrav = New System.Windows.Forms.Label()
        Me.TxtPercIIBB = New System.Windows.Forms.TextBox()
        Me.LblPercIIBB = New System.Windows.Forms.Label()
        Me.TxtTotal = New System.Windows.Forms.TextBox()
        Me.LblTotal = New System.Windows.Forms.Label()
        Me.GroupBox1 = New System.Windows.Forms.GroupBox()
        Me.BtnCerrar = New System.Windows.Forms.Button()
        Me.BtnProveedor = New System.Windows.Forms.Button()
        Me.BtnRubro = New System.Windows.Forms.Button()
        Me.BtnGuardar = New System.Windows.Forms.Button()
        Me.Cant = New System.Windows.Forms.DataGridViewTextBoxColumn()
        Me.Descripcion = New System.Windows.Forms.DataGridViewTextBoxColumn()
        Me.CCosto = New System.Windows.Forms.DataGridViewComboBoxColumn()
        Me.Rubro = New System.Windows.Forms.DataGridViewComboBoxColumn()
        Me.ImporteSinIVA = New System.Windows.Forms.DataGridViewTextBoxColumn()
        Me.porcIVA = New System.Windows.Forms.DataGridViewTextBoxColumn()
        Me.ImporteIVA = New System.Windows.Forms.DataGridViewTextBoxColumn()
        CType(Me.DTGVDetCompras, System.ComponentModel.ISupportInitialize).BeginInit()
        Me.GroupBox1.SuspendLayout()
        Me.SuspendLayout()
        '
        'DTPFecha
        '
        Me.DTPFecha.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.DTPFecha.Format = System.Windows.Forms.DateTimePickerFormat.[Short]
        Me.DTPFecha.Location = New System.Drawing.Point(45, 9)
        Me.DTPFecha.Name = "DTPFecha"
        Me.DTPFecha.Size = New System.Drawing.Size(110, 22)
        Me.DTPFecha.TabIndex = 0
        '
        'LblFecha
        '
        Me.LblFecha.AutoSize = True
        Me.LblFecha.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.LblFecha.ForeColor = System.Drawing.Color.White
        Me.LblFecha.Location = New System.Drawing.Point(4, 13)
        Me.LblFecha.Name = "LblFecha"
        Me.LblFecha.Size = New System.Drawing.Size(42, 14)
        Me.LblFecha.TabIndex = 1
        Me.LblFecha.Text = "Fecha"
        '
        'LblProveedor
        '
        Me.LblProveedor.AutoSize = True
        Me.LblProveedor.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.LblProveedor.ForeColor = System.Drawing.Color.White
        Me.LblProveedor.Location = New System.Drawing.Point(169, 13)
        Me.LblProveedor.Name = "LblProveedor"
        Me.LblProveedor.Size = New System.Drawing.Size(70, 14)
        Me.LblProveedor.TabIndex = 2
        Me.LblProveedor.Text = "Proveedor"
        '
        'CmbProveedor
        '
        Me.CmbProveedor.FormattingEnabled = True
        Me.CmbProveedor.Location = New System.Drawing.Point(239, 8)
        Me.CmbProveedor.Name = "CmbProveedor"
        Me.CmbProveedor.Size = New System.Drawing.Size(522, 22)
        Me.CmbProveedor.TabIndex = 3
        '
        'LblLetraDoc
        '
        Me.LblLetraDoc.AutoSize = True
        Me.LblLetraDoc.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.LblLetraDoc.ForeColor = System.Drawing.Color.White
        Me.LblLetraDoc.Location = New System.Drawing.Point(771, 12)
        Me.LblLetraDoc.Name = "LblLetraDoc"
        Me.LblLetraDoc.Size = New System.Drawing.Size(42, 14)
        Me.LblLetraDoc.TabIndex = 4
        Me.LblLetraDoc.Text = "Letra"
        '
        'CmbLetraDoc
        '
        Me.CmbLetraDoc.FormattingEnabled = True
        Me.CmbLetraDoc.Items.AddRange(New Object() {"A", "B", "C", "X"})
        Me.CmbLetraDoc.Location = New System.Drawing.Point(813, 8)
        Me.CmbLetraDoc.Name = "CmbLetraDoc"
        Me.CmbLetraDoc.Size = New System.Drawing.Size(42, 22)
        Me.CmbLetraDoc.TabIndex = 5
        '
        'CmbTipoDoc
        '
        Me.CmbTipoDoc.AutoCompleteCustomSource.AddRange(New String() {"A", "B", "C", "X"})
        Me.CmbTipoDoc.FormattingEnabled = True
        Me.CmbTipoDoc.Items.AddRange(New Object() {"Factura", "Nota de Credito", "Nota de Debito"})
        Me.CmbTipoDoc.Location = New System.Drawing.Point(907, 8)
        Me.CmbTipoDoc.Name = "CmbTipoDoc"
        Me.CmbTipoDoc.Size = New System.Drawing.Size(127, 22)
        Me.CmbTipoDoc.TabIndex = 7
        '
        'LblTipoDoc
        '
        Me.LblTipoDoc.AutoSize = True
        Me.LblTipoDoc.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.LblTipoDoc.ForeColor = System.Drawing.Color.White
        Me.LblTipoDoc.Location = New System.Drawing.Point(874, 12)
        Me.LblTipoDoc.Name = "LblTipoDoc"
        Me.LblTipoDoc.Size = New System.Drawing.Size(35, 14)
        Me.LblTipoDoc.TabIndex = 6
        Me.LblTipoDoc.Text = "Tipo"
        '
        'LblNDoc
        '
        Me.LblNDoc.AutoSize = True
        Me.LblNDoc.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.LblNDoc.ForeColor = System.Drawing.Color.White
        Me.LblNDoc.Location = New System.Drawing.Point(1050, 12)
        Me.LblNDoc.Name = "LblNDoc"
        Me.LblNDoc.Size = New System.Drawing.Size(105, 14)
        Me.LblNDoc.TabIndex = 8
        Me.LblNDoc.Text = "Nro. Documento"
        '
        'TxtNumDoc
        '
        Me.TxtNumDoc.Location = New System.Drawing.Point(1167, 8)
        Me.TxtNumDoc.Name = "TxtNumDoc"
        Me.TxtNumDoc.Size = New System.Drawing.Size(142, 22)
        Me.TxtNumDoc.TabIndex = 9
        '
        'DTGVDetCompras
        '
        Me.DTGVDetCompras.BackgroundColor = System.Drawing.Color.AliceBlue
        Me.DTGVDetCompras.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
        Me.DTGVDetCompras.Columns.AddRange(New System.Windows.Forms.DataGridViewColumn() {Me.Cant, Me.Descripcion, Me.CCosto, Me.Rubro, Me.ImporteSinIVA, Me.porcIVA, Me.ImporteIVA})
        Me.DTGVDetCompras.Location = New System.Drawing.Point(8, 40)
        Me.DTGVDetCompras.Name = "DTGVDetCompras"
        Me.DTGVDetCompras.Size = New System.Drawing.Size(1300, 431)
        Me.DTGVDetCompras.TabIndex = 10
        '
        'TxtSubtotal
        '
        Me.TxtSubtotal.Location = New System.Drawing.Point(1167, 480)
        Me.TxtSubtotal.Name = "TxtSubtotal"
        Me.TxtSubtotal.Size = New System.Drawing.Size(142, 22)
        Me.TxtSubtotal.TabIndex = 12
        '
        'LblSubtotal
        '
        Me.LblSubtotal.AutoSize = True
        Me.LblSubtotal.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.LblSubtotal.ForeColor = System.Drawing.Color.White
        Me.LblSubtotal.Location = New System.Drawing.Point(1010, 484)
        Me.LblSubtotal.Name = "LblSubtotal"
        Me.LblSubtotal.Size = New System.Drawing.Size(63, 14)
        Me.LblSubtotal.TabIndex = 11
        Me.LblSubtotal.Text = "Subtotal"
        '
        'TxtIVA
        '
        Me.TxtIVA.Location = New System.Drawing.Point(1167, 508)
        Me.TxtIVA.Name = "TxtIVA"
        Me.TxtIVA.Size = New System.Drawing.Size(142, 22)
        Me.TxtIVA.TabIndex = 14
        '
        'LblIVA
        '
        Me.LblIVA.AutoSize = True
        Me.LblIVA.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.LblIVA.ForeColor = System.Drawing.Color.White
        Me.LblIVA.Location = New System.Drawing.Point(1010, 512)
        Me.LblIVA.Name = "LblIVA"
        Me.LblIVA.Size = New System.Drawing.Size(28, 14)
        Me.LblIVA.TabIndex = 13
        Me.LblIVA.Text = "IVA"
        '
        'TxtCNoGrav
        '
        Me.TxtCNoGrav.Location = New System.Drawing.Point(1167, 566)
        Me.TxtCNoGrav.Name = "TxtCNoGrav"
        Me.TxtCNoGrav.Size = New System.Drawing.Size(142, 22)
        Me.TxtCNoGrav.TabIndex = 18
        '
        'LblCNoGrav
        '
        Me.LblCNoGrav.AutoSize = True
        Me.LblCNoGrav.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.LblCNoGrav.ForeColor = System.Drawing.Color.White
        Me.LblCNoGrav.Location = New System.Drawing.Point(1010, 570)
        Me.LblCNoGrav.Name = "LblCNoGrav"
        Me.LblCNoGrav.Size = New System.Drawing.Size(154, 14)
        Me.LblCNoGrav.TabIndex = 17
        Me.LblCNoGrav.Text = "Conceptos No Gravados"
        '
        'TxtPercIIBB
        '
        Me.TxtPercIIBB.Location = New System.Drawing.Point(1167, 538)
        Me.TxtPercIIBB.Name = "TxtPercIIBB"
        Me.TxtPercIIBB.Size = New System.Drawing.Size(142, 22)
        Me.TxtPercIIBB.TabIndex = 16
        '
        'LblPercIIBB
        '
        Me.LblPercIIBB.AutoSize = True
        Me.LblPercIIBB.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.LblPercIIBB.ForeColor = System.Drawing.Color.White
        Me.LblPercIIBB.Location = New System.Drawing.Point(1010, 542)
        Me.LblPercIIBB.Name = "LblPercIIBB"
        Me.LblPercIIBB.Size = New System.Drawing.Size(70, 14)
        Me.LblPercIIBB.TabIndex = 15
        Me.LblPercIIBB.Text = "Perc IIBB"
        '
        'TxtTotal
        '
        Me.TxtTotal.Location = New System.Drawing.Point(1167, 594)
        Me.TxtTotal.Name = "TxtTotal"
        Me.TxtTotal.Size = New System.Drawing.Size(142, 22)
        Me.TxtTotal.TabIndex = 20
        '
        'LblTotal
        '
        Me.LblTotal.AutoSize = True
        Me.LblTotal.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.LblTotal.ForeColor = System.Drawing.Color.White
        Me.LblTotal.Location = New System.Drawing.Point(1010, 598)
        Me.LblTotal.Name = "LblTotal"
        Me.LblTotal.Size = New System.Drawing.Size(42, 14)
        Me.LblTotal.TabIndex = 19
        Me.LblTotal.Text = "Total"
        '
        'GroupBox1
        '
        Me.GroupBox1.Controls.Add(Me.BtnCerrar)
        Me.GroupBox1.Controls.Add(Me.BtnProveedor)
        Me.GroupBox1.Controls.Add(Me.BtnRubro)
        Me.GroupBox1.Controls.Add(Me.BtnGuardar)
        Me.GroupBox1.Location = New System.Drawing.Point(13, 533)
        Me.GroupBox1.Name = "GroupBox1"
        Me.GroupBox1.Size = New System.Drawing.Size(991, 79)
        Me.GroupBox1.TabIndex = 21
        Me.GroupBox1.TabStop = False
        '
        'BtnCerrar
        '
        Me.BtnCerrar.Location = New System.Drawing.Point(818, 30)
        Me.BtnCerrar.Name = "BtnCerrar"
        Me.BtnCerrar.Size = New System.Drawing.Size(166, 27)
        Me.BtnCerrar.TabIndex = 3
        Me.BtnCerrar.Text = "Cerrar"
        Me.BtnCerrar.UseVisualStyleBackColor = True
        '
        'BtnProveedor
        '
        Me.BtnProveedor.Location = New System.Drawing.Point(547, 30)
        Me.BtnProveedor.Name = "BtnProveedor"
        Me.BtnProveedor.Size = New System.Drawing.Size(166, 27)
        Me.BtnProveedor.TabIndex = 2
        Me.BtnProveedor.Text = "Agregar Proveedor"
        Me.BtnProveedor.UseVisualStyleBackColor = True
        '
        'BtnRubro
        '
        Me.BtnRubro.Location = New System.Drawing.Point(276, 30)
        Me.BtnRubro.Name = "BtnRubro"
        Me.BtnRubro.Size = New System.Drawing.Size(166, 27)
        Me.BtnRubro.TabIndex = 1
        Me.BtnRubro.Text = "Agregar Rubro"
        Me.BtnRubro.UseVisualStyleBackColor = True
        '
        'BtnGuardar
        '
        Me.BtnGuardar.Location = New System.Drawing.Point(5, 30)
        Me.BtnGuardar.Name = "BtnGuardar"
        Me.BtnGuardar.Size = New System.Drawing.Size(166, 27)
        Me.BtnGuardar.TabIndex = 0
        Me.BtnGuardar.Text = "Guardar Registro"
        Me.BtnGuardar.UseVisualStyleBackColor = True
        '
        'Cant
        '
        Me.Cant.HeaderText = "Cant."
        Me.Cant.Name = "Cant"
        Me.Cant.Resizable = System.Windows.Forms.DataGridViewTriState.[False]
        Me.Cant.Width = 70
        '
        'Descripcion
        '
        Me.Descripcion.HeaderText = "Producto / Servicio"
        Me.Descripcion.Name = "Descripcion"
        Me.Descripcion.Resizable = System.Windows.Forms.DataGridViewTriState.[False]
        Me.Descripcion.Width = 455
        '
        'CCosto
        '
        Me.CCosto.DisplayStyle = System.Windows.Forms.DataGridViewComboBoxDisplayStyle.ComboBox
        Me.CCosto.HeaderText = "Centro de Costos"
        Me.CCosto.Items.AddRange(New Object() {"Adm. General", "Agricultura", "Ganaderia"})
        Me.CCosto.Name = "CCosto"
        Me.CCosto.Resizable = System.Windows.Forms.DataGridViewTriState.[False]
        Me.CCosto.SortMode = System.Windows.Forms.DataGridViewColumnSortMode.Automatic
        Me.CCosto.Width = 160
        '
        'Rubro
        '
        Me.Rubro.DataPropertyName = "IdRubro"
        Me.Rubro.DisplayStyle = System.Windows.Forms.DataGridViewComboBoxDisplayStyle.ComboBox
        Me.Rubro.HeaderText = "Rubro"
        Me.Rubro.Name = "Rubro"
        Me.Rubro.Resizable = System.Windows.Forms.DataGridViewTriState.[False]
        Me.Rubro.SortMode = System.Windows.Forms.DataGridViewColumnSortMode.Programmatic
        Me.Rubro.Width = 190
        '
        'ImporteSinIVA
        '
        Me.ImporteSinIVA.HeaderText = "Importe sin IVA"
        Me.ImporteSinIVA.Name = "ImporteSinIVA"
        Me.ImporteSinIVA.Resizable = System.Windows.Forms.DataGridViewTriState.[False]
        Me.ImporteSinIVA.Width = 180
        '
        'porcIVA
        '
        Me.porcIVA.HeaderText = "IVA(%)"
        Me.porcIVA.Name = "porcIVA"
        Me.porcIVA.Resizable = System.Windows.Forms.DataGridViewTriState.[False]
        Me.porcIVA.Width = 50
        '
        'ImporteIVA
        '
        Me.ImporteIVA.HeaderText = "IVA ($)"
        Me.ImporteIVA.Name = "ImporteIVA"
        Me.ImporteIVA.Resizable = System.Windows.Forms.DataGridViewTriState.[False]
        Me.ImporteIVA.Width = 150
        '
        'FrmComprasGrales
        '
        Me.AutoScaleDimensions = New System.Drawing.SizeF(7.0!, 14.0!)
        Me.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font
        Me.AutoSize = True
        Me.AutoSizeMode = System.Windows.Forms.AutoSizeMode.GrowAndShrink
        Me.BackColor = System.Drawing.Color.SteelBlue
        Me.ClientSize = New System.Drawing.Size(1316, 622)
        Me.Controls.Add(Me.GroupBox1)
        Me.Controls.Add(Me.TxtTotal)
        Me.Controls.Add(Me.LblTotal)
        Me.Controls.Add(Me.TxtCNoGrav)
        Me.Controls.Add(Me.LblCNoGrav)
        Me.Controls.Add(Me.TxtPercIIBB)
        Me.Controls.Add(Me.LblPercIIBB)
        Me.Controls.Add(Me.TxtIVA)
        Me.Controls.Add(Me.LblIVA)
        Me.Controls.Add(Me.TxtSubtotal)
        Me.Controls.Add(Me.LblSubtotal)
        Me.Controls.Add(Me.DTGVDetCompras)
        Me.Controls.Add(Me.TxtNumDoc)
        Me.Controls.Add(Me.LblNDoc)
        Me.Controls.Add(Me.CmbTipoDoc)
        Me.Controls.Add(Me.LblTipoDoc)
        Me.Controls.Add(Me.CmbLetraDoc)
        Me.Controls.Add(Me.LblLetraDoc)
        Me.Controls.Add(Me.CmbProveedor)
        Me.Controls.Add(Me.LblProveedor)
        Me.Controls.Add(Me.LblFecha)
        Me.Controls.Add(Me.DTPFecha)
        Me.Font = New System.Drawing.Font("Consolas", 9.0!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedSingle
        Me.Name = "FrmComprasGrales"
        Me.StartPosition = System.Windows.Forms.FormStartPosition.Manual
        Me.Text = "Formulario Compras Generales"
        Me.WindowState = System.Windows.Forms.FormWindowState.Maximized
        CType(Me.DTGVDetCompras, System.ComponentModel.ISupportInitialize).EndInit()
        Me.GroupBox1.ResumeLayout(False)
        Me.ResumeLayout(False)
        Me.PerformLayout()

    End Sub
    Friend WithEvents DTPFecha As System.Windows.Forms.DateTimePicker
    Friend WithEvents LblFecha As System.Windows.Forms.Label
    Friend WithEvents LblProveedor As System.Windows.Forms.Label
    Friend WithEvents CmbProveedor As System.Windows.Forms.ComboBox
    Friend WithEvents LblLetraDoc As System.Windows.Forms.Label
    Friend WithEvents CmbLetraDoc As System.Windows.Forms.ComboBox
    Friend WithEvents CmbTipoDoc As System.Windows.Forms.ComboBox
    Friend WithEvents LblTipoDoc As System.Windows.Forms.Label
    Friend WithEvents LblNDoc As System.Windows.Forms.Label
    Friend WithEvents TxtNumDoc As System.Windows.Forms.TextBox
    Friend WithEvents DTGVDetCompras As System.Windows.Forms.DataGridView
    Friend WithEvents TxtSubtotal As System.Windows.Forms.TextBox
    Friend WithEvents LblSubtotal As System.Windows.Forms.Label
    Friend WithEvents TxtIVA As System.Windows.Forms.TextBox
    Friend WithEvents LblIVA As System.Windows.Forms.Label
    Friend WithEvents TxtCNoGrav As System.Windows.Forms.TextBox
    Friend WithEvents LblCNoGrav As System.Windows.Forms.Label
    Friend WithEvents TxtPercIIBB As System.Windows.Forms.TextBox
    Friend WithEvents LblPercIIBB As System.Windows.Forms.Label
    Friend WithEvents TxtTotal As System.Windows.Forms.TextBox
    Friend WithEvents LblTotal As System.Windows.Forms.Label
    Friend WithEvents GroupBox1 As System.Windows.Forms.GroupBox
    Friend WithEvents BtnCerrar As System.Windows.Forms.Button
    Friend WithEvents BtnProveedor As System.Windows.Forms.Button
    Friend WithEvents BtnRubro As System.Windows.Forms.Button
    Friend WithEvents BtnGuardar As System.Windows.Forms.Button
    Friend WithEvents Cant As System.Windows.Forms.DataGridViewTextBoxColumn
    Friend WithEvents Descripcion As System.Windows.Forms.DataGridViewTextBoxColumn
    Friend WithEvents CCosto As System.Windows.Forms.DataGridViewComboBoxColumn
    Friend WithEvents Rubro As System.Windows.Forms.DataGridViewComboBoxColumn
    Friend WithEvents ImporteSinIVA As System.Windows.Forms.DataGridViewTextBoxColumn
    Friend WithEvents porcIVA As System.Windows.Forms.DataGridViewTextBoxColumn
    Friend WithEvents ImporteIVA As System.Windows.Forms.DataGridViewTextBoxColumn
End Class
