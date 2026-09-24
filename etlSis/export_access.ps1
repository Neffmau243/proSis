param(
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$sourcePath = (Resolve-Path -LiteralPath $Source).Path
$outputPath = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath (Join-Path $outputPath 'manifest.json')) {
    throw 'The extraction already exists. Use a new output directory.'
}
[IO.Directory]::CreateDirectory($outputPath) | Out-Null
$before = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
$connection = New-Object -ComObject ADODB.Connection
$connection.Mode = 1 # adModeRead; SELECT only, never repair/compact the source.
$manifest = [ordered]@{ version = 1; reader = 'Microsoft.ACE.OLEDB.16.0'; source_sha256 = $before; tables = @() }
try {
    $connection.Open('Provider=Microsoft.ACE.OLEDB.16.0;Data Source=' + $sourcePath + ';Mode=Read;')
    $schema = $connection.OpenSchema(20) # adSchemaTables
    $names = @()
    while (-not $schema.EOF) {
        if ($schema.Fields.Item('TABLE_TYPE').Value -eq 'TABLE') {
            $names += [string]$schema.Fields.Item('TABLE_NAME').Value
        }
        $schema.MoveNext()
    }
    $schema.Close()
    $ordinal = 0
    foreach ($table in ($names | Sort-Object)) {
        $filename = ('table-{0:D3}.jsonl' -f $ordinal)
        $ordinal++
        $recordset = $connection.Execute('SELECT * FROM [' + $table.Replace(']', ']]') + ']')
        $columns = @()
        for ($i=0; $i -lt $recordset.Fields.Count; $i++) {
            $field = $recordset.Fields.Item($i)
            $columns += [ordered]@{ name=[string]$field.Name; ado_type=[int]$field.Type; size=[int]$field.DefinedSize }
        }
        $writer = [IO.StreamWriter]::new((Join-Path $outputPath $filename), $false, [Text.UTF8Encoding]::new($false))
        $row = 0
        try {
            while (-not $recordset.EOF) {
                $batch = $recordset.GetRows(1000)
                for ($record=0; $record -lt $batch.GetLength(1); $record++) {
                $values = [ordered]@{}
                for ($i=0; $i -lt $columns.Count; $i++) {
                    $value = $batch[$i,$record]
                    if ($null -eq $value -or $value -is [DBNull]) { $value = $null }
                    elseif ($value -is [DateTime]) { $value = $value.ToString('yyyy-MM-ddTHH:mm:ss.fffffff', [Globalization.CultureInfo]::InvariantCulture) }
                    elseif ($value -is [byte[]]) { $value = @{ '$binary_base64' = [Convert]::ToBase64String($value) } }
                    $values[[string]$columns[$i].name] = $value
                }
                $writer.WriteLine((ConvertTo-Json -InputObject $values -Depth 20 -Compress))
                $row++
                }
            }
        } finally { $writer.Dispose(); $recordset.Close() }
        $countResult = $connection.Execute('SELECT COUNT(*) AS n FROM [' + $table.Replace(']', ']]') + ']')
        $expected = [int]$countResult.Fields.Item('n').Value
        $countResult.Close()
        # Jet can expose stale COUNT(*) metadata. Preserve the discrepancy; do
        # not invent rows or compact/repair the original to hide it.
        $manifest.tables += [ordered]@{ name=$table; file=$filename; rows=$row; reported_count=$expected; count_mismatch=($row -ne $expected); columns=$columns; sha256=(Get-FileHash -LiteralPath (Join-Path $outputPath $filename) -Algorithm SHA256).Hash.ToLowerInvariant() }
        Write-Output ('Extracted {0}: {1} rows' -f $table,$row)
    }
} finally {
    if ($connection.State -eq 1) { $connection.Close() }
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($connection)
}
$after = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($before -ne $after) { throw 'Source changed during extraction. No valid manifest was published.' }
[IO.File]::WriteAllText((Join-Path $outputPath 'manifest.json'), (ConvertTo-Json -InputObject $manifest -Depth 20), [Text.UTF8Encoding]::new($false))
