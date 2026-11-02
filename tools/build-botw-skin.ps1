param(
    [Parameter(Mandatory = $true)]
    [string]$AssetDirectory
)

$ErrorActionPreference = 'Stop'
$destination = Join-Path $PSScriptRoot '..\static\skins\botw'
[System.IO.Directory]::CreateDirectory($destination) | Out-Null
$assets = (Resolve-Path $AssetDirectory).Path
. (Join-Path $PSScriptRoot 'bitmap-assets.ps1')

Export-Asset 'header.jpg' 'header.png' '' '1200x'
foreach ($variant in @(@('control', 0), @('control-hover', 912), @('control-dark', 1824))) {
    Export-Asset 'buttons.jpg' "$($variant[0]).png" "912x912+$($variant[1])+0" '650x'
}
Export-Asset 'scrolls.jpg' 'frame.png' '1000x1280+0+0' '900x'
Export-Asset 'scrolls.jpg' 'scroll.png' '920x1280+1000+0' '800x'
foreach ($icon in @(
    @('heart', 0, 0), @('compass', 800, 0),
    @('sword', 0, 800), @('gem', 800, 800)
)) {
    Export-Asset 'icons.jpg' "$($icon[0]).png" "800x800+$($icon[1])+$($icon[2])" '160x160'
}
Export-Asset 'jewel-button.jpg' 'jewel.png' '640x1280+0+0' '500x'
& magick (Join-Path $assets 'bg.jpg') '-quality' '88' `
    (Join-Path $destination 'scenery.webp')
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to generate scenery.webp'
}
