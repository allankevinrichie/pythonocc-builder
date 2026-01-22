# Windows build script for 3rd-party dependencies and OCCT
param (
    [string]$SrcDir = "src",
    [string]$InstallDir = "install",
    [string]$BuildDir = "build"
)

$ErrorActionPreference = "Stop"

$SrcDir = Resolve-Path $SrcDir
$InstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$BuildDir = [System.IO.Path]::GetFullPath($BuildDir)

Write-Host "Source Dir: $SrcDir"
Write-Host "Install Dir: $InstallDir"
Write-Host "Build Dir: $BuildDir"

if (!(Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir | Out-Null }
if (!(Test-Path $BuildDir)) { New-Item -ItemType Directory -Path $BuildDir | Out-Null }

# 1. Build FreeType
$FreeTypeSrc = Get-ChildItem "$SrcDir/3rdparty/freetype-*.tar.gz" | Select-Object -First 1
if ($FreeTypeSrc) {
    Write-Host "Building FreeType..."
    $FreeTypeBuildDir = "$BuildDir/freetype"
    if (Test-Path $FreeTypeBuildDir) { Remove-Item -Recurse -Force $FreeTypeBuildDir }
    New-Item -ItemType Directory -Path $FreeTypeBuildDir | Out-Null
    
    tar -xzf $FreeTypeSrc.FullName -C $BuildDir
    $FreeTypeExtracted = Get-ChildItem "$BuildDir/freetype-*" | Where-Object { $_.PSIsContainer } | Select-Object -First 1
    
    Push-Location $FreeTypeBuildDir
    cmake $FreeTypeExtracted.FullName `
        -DCMAKE_INSTALL_PREFIX="$InstallDir/freetype" `
        -DCMAKE_BUILD_TYPE=Release `
        -DBUILD_SHARED_LIBS=ON
    cmake --build . --config Release --target install
    Pop-Location
}

# 2. Build Tcl/Tk (Windows usually needs pre-built binaries or nmake, skipping for now as OCCT on Windows often uses pre-built Tcl/Tk)
# For simplicity, we might assume Tcl/Tk is provided or we download a pre-built version.
# However, to be consistent with Linux, we should build it. But Tcl/Tk build on Windows is complex (nmake).
# Let's use a pre-built Tcl/Tk or rely on choco/vcpkg if possible. 
# For now, let's assume we can skip Tcl/Tk build script complexity and use what's available or minimal.
# ACTUALLY: OCCT requires Tcl/Tk. We can try to build it using CMake if available (Tcl 8.7+ has cmake, 8.6 not really).
# Easier: Download Magics. Or just skip for a moment and see if we can get by with system libs? No system libs on Windows.
# STRATEGY: Use vcpkg for dependencies on Windows is much easier.

# 3. Build OCCT
# We need Tcl/Tk. Let's assume we use vcpkg to install them in the CI workflow.
# So this script mainly orchestrates OCCT build pointing to those libs.

Write-Host "Building OCCT..."
$OcctSrc = "$SrcDir/occt"
$OcctBuildDir = "$BuildDir/occt"
if (Test-Path $OcctBuildDir) { Remove-Item -Recurse -Force $OcctBuildDir }
New-Item -ItemType Directory -Path $OcctBuildDir | Out-Null

Push-Location $OcctBuildDir

# Note: We expect dependencies to be provided via CMAKE_PREFIX_PATH or specific vars
# In CI, we will use vcpkg to provide freetype, tcl, tk.

cmake $OcctSrc `
    -DCMAKE_INSTALL_PREFIX="$InstallDir/occt" `
    -DCMAKE_BUILD_TYPE=Release `
    -DUSE_FREETYPE=ON `
    -DUSE_TCL=ON `
    -DUSE_TK=ON `
    -DCMAKE_TOOLCHAIN_FILE="$env:VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" `
    -DVCPKG_TARGET_TRIPLET=x64-windows

cmake --build . --config Release --target install
Pop-Location

Write-Host "Windows 3rd-party build complete."
