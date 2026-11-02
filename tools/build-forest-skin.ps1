param(
    [Parameter(Mandatory = $true)]
    [string]$ReferenceImage
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$destination = Join-Path $PSScriptRoot '..\static\skins\forest'
$source = [System.Drawing.Bitmap]::FromFile((Resolve-Path $ReferenceImage))

function Export-Crop($Name, $X, $Y, $Width, $Height, $Slice = 0) {
    $rectangle = [System.Drawing.Rectangle]::new($X, $Y, $Width, $Height)
    $crop = $source.Clone($rectangle, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try {
        if ($Slice -gt 0) {
            $graphics = [System.Drawing.Graphics]::FromImage($crop)
            try {
                $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
                $graphics.FillRectangle([System.Drawing.Brushes]::Transparent,
                    $Slice, $Slice, ($Width - 2 * $Slice), ($Height - 2 * $Slice))
            } finally {
                $graphics.Dispose()
            }
        }
        $format = [System.Drawing.Imaging.ImageFormat]::Png
        if ($Name.EndsWith('.jpg')) {
            $format = [System.Drawing.Imaging.ImageFormat]::Jpeg
        }
        $crop.Save((Join-Path $destination $Name), $format)
    } finally {
        $crop.Dispose()
    }
}

try {
    if ($source.Width -ne 864 -or $source.Height -ne 1920) {
        throw 'Expected the original 864 x 1920 theme1.jpeg reference.'
    }
    # Nine-slice centers are not painted, so embedded reference labels are excluded.
    Export-Crop 'control.png' 94 590 215 77 16
    Export-Crop 'inset.png' 123 1224 619 236 30

    $texture = $source.Clone([System.Drawing.Rectangle]::new(170, 1325, 290, 75),
        [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $surface = [System.Drawing.Bitmap]::new(580, 150)
    $graphics = [System.Drawing.Graphics]::FromImage($surface)
    try {
        # Mirrored tiles meet without visible lighting seams.
        $graphics.DrawImageUnscaled($texture, 0, 0)
        $texture.RotateFlip([System.Drawing.RotateFlipType]::RotateNoneFlipX)
        $graphics.DrawImageUnscaled($texture, 290, 0)
        $texture.RotateFlip([System.Drawing.RotateFlipType]::RotateNoneFlipY)
        $graphics.DrawImageUnscaled($texture, 290, 75)
        $texture.RotateFlip([System.Drawing.RotateFlipType]::RotateNoneFlipX)
        $graphics.DrawImageUnscaled($texture, 0, 75)
        $surface.Save((Join-Path $destination 'surface.jpg'),
            [System.Drawing.Imaging.ImageFormat]::Jpeg)
    } finally {
        $graphics.Dispose()
        $surface.Dispose()
        $texture.Dispose()
    }

    # Assemble clean edge samples; the original long sides also contain controls.
    $frame = [System.Drawing.Bitmap]::new(256, 256)
    $graphics = [System.Drawing.Graphics]::FromImage($frame)
    try {
        $patches = @(
            @(0, 0, 38, 38, 68, 373, 38, 38),
            @(218, 0, 38, 38, 754, 373, 38, 38),
            @(0, 218, 38, 38, 68, 927, 38, 38),
            @(218, 218, 38, 38, 754, 927, 38, 38),
            @(38, 0, 90, 38, 218, 373, 150, 38),
            @(128, 0, 90, 38, 485, 373, 150, 38),
            @(38, 218, 180, 38, 310, 927, 200, 38),
            @(0, 38, 38, 180, 68, 674, 38, 24),
            @(218, 38, 38, 180, 754, 674, 38, 24)
        )
        foreach ($patch in $patches) {
            $graphics.DrawImage($source,
                [System.Drawing.Rectangle]::new($patch[0], $patch[1], $patch[2], $patch[3]),
                $patch[4], $patch[5], $patch[6], $patch[7],
                [System.Drawing.GraphicsUnit]::Pixel)
        }
        $frame.Save((Join-Path $destination 'frame.png'),
            [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose()
        $frame.Dispose()
    }

    $emblem = [System.Drawing.Bitmap]::new(108, 108)
    $graphics = [System.Drawing.Graphics]::FromImage($emblem)
    try {
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $clip = [System.Drawing.Drawing2D.GraphicsPath]::new()
        try {
            $clip.AddEllipse(1, 1, 106, 106)
            $graphics.SetClip($clip)
            $graphics.DrawImage($source, [System.Drawing.Rectangle]::new(0, 0, 108, 108),
                373, 330, 108, 108, [System.Drawing.GraphicsUnit]::Pixel)
        } finally {
            $clip.Dispose()
        }
        $emblem.Save((Join-Path $destination 'emblem.png'),
            [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose()
        $emblem.Dispose()
    }

    # Retain the castle and forest edges, masking the reference's UI completely.
    $background = $source.Clone([System.Drawing.Rectangle]::new(0, 224, 864, 1696),
        [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($background)
    try {
        $mask = [System.Drawing.SolidBrush]::new(
            [System.Drawing.ColorTranslator]::FromHtml('#101616'))
        try {
            $graphics.FillRectangle($mask, 50, 106, 764, 1590)
        } finally {
            $mask.Dispose()
        }
        for ($row = 60; $row -lt 106; $row++) {
            $alpha = [int](255 * ($row - 60) / 45)
            $fade = [System.Drawing.SolidBrush]::new(
                [System.Drawing.Color]::FromArgb($alpha, 16, 22, 22))
            try {
                $graphics.FillRectangle($fade, 50, $row, 764, 1)
            } finally {
                $fade.Dispose()
            }
        }
        $background.Save((Join-Path $destination 'backdrop.jpg'),
            [System.Drawing.Imaging.ImageFormat]::Jpeg)
    } finally {
        $graphics.Dispose()
        $background.Dispose()
    }
} finally {
    $source.Dispose()
}
