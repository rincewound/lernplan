function Export-Asset($Source, $Name, $Crop, $Resize) {
    $arguments = @((Join-Path $assets $Source))
    if ($Crop) {
        $arguments += @('-crop', $Crop, '+repage')
    }
    # Preserve colored highlights while removing the white backing and enclosed gaps.
    $arguments += @('-bordercolor', 'white', '-border', '1',
        '-alpha', 'set', '-fuzz', '12%', '-fill', 'none',
        '-draw', 'alpha 0,0 floodfill',
        '-channel', 'A', '-fx',
        'min(a,max(r,max(g,b))-min(r,min(g,b))>0.08 ? 1 : min(1,(1-min(r,min(g,b)))/0.6))',
        '+channel', '-trim', '+repage')
    if ($Resize) {
        $arguments += @('-resize', $Resize)
    }
    $arguments += (Join-Path $destination $Name)
    & magick @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to generate $Name from $Source"
    }
}
