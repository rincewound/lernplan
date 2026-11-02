param(
    [Parameter(Mandatory = $true)]
    [string]$AssetDirectory
)

$ErrorActionPreference = 'Stop'
$destination = Join-Path $PSScriptRoot '..\static\skins\lotr'
[System.IO.Directory]::CreateDirectory($destination) | Out-Null
$assets = (Resolve-Path $AssetDirectory).Path

. (Join-Path $PSScriptRoot 'bitmap-assets.ps1')

# The supplied .jpg files contain WebP data; ImageMagick detects their real format.
Export-Asset 'header.jpg' 'header.png' '1040x340+0+205' '1000x'
Export-Asset 'buttons.jpg' 'control.png' '912x912+0+0' '650x'
Export-Asset 'buttons.jpg' 'control-hover.png' '912x912+912+0' '650x'
Export-Asset 'buttons.jpg' 'control-bronze.png' '912x912+1824+0' '650x'
& magick (Join-Path $destination 'control.png') '-channel' 'R' '-evaluate' `
    'multiply' '0.65' '+channel' (Join-Path $destination 'control-green.png')
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to generate control-green.png'
}
Export-Asset 'scroll_msg.jpg' 'scroll.png' '' '1400x'
Export-Asset 'scroll_bg.jpg' 'paper.png' '' '1000x'

foreach ($icon in @(
    @('unicorn.png', 0, 0), @('pegasus.png', 560, 0),
    @('emblem.png', 1120, 0), @('sword.png', 1680, 0),
    @('shield.png', 0, 560), @('feather.png', 560, 560),
    @('laurel.png', 1120, 560), @('castle.png', 1680, 560)
)) {
    Export-Asset 'icons.jpg' $icon[0] "560x560+$($icon[1])+$($icon[2])" '160x160'
}

& magick (Join-Path $assets 'background.jpg') '-quality' '88' `
    (Join-Path $destination 'scenery.webp')
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to generate scenery.webp'
}
