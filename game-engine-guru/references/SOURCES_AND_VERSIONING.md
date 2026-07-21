# Sources and Versioning

Last public-source review: **2026-07-21**

Use this ledger for volatile API, language, platform, and specification claims. Public sources do not replace current console SDK documentation, certification rules, vendor integration guides, or measurements on target hardware.

## Maintenance policy

1. Prefer specifications, vendor documentation, standards papers, and upstream repositories.
2. Label previews, research, leaks, and proprietary implementation inferences explicitly.
3. Capability-query APIs and toolchains; never branch from a marketing name alone.
4. Record the SDK/compiler/driver used by benchmarks and avoid universal timing claims.
5. Recheck volatile entries at least quarterly and before changing a production baseline.

## Graphics and storage

- Shader Model 6.8 and Work Graphs:
  <https://microsoft.github.io/DirectX-Specs/d3d/HLSL_ShaderModel6_8.html>
- D3D12 Work Graphs specification:
  <https://microsoft.github.io/DirectX-Specs/d3d/WorkGraphs.html>
- Mesh Nodes preview (Shader Model 6.9 opt-in path):
  <https://devblogs.microsoft.com/directx/d3d12-mesh-nodes-in-work-graphs/>
- Shader Model enumeration and runtime capability query:
  <https://learn.microsoft.com/windows/win32/api/d3d12/ne-d3d12-d3d_shader_model>
- DirectStorage 1.4 Zstandard public preview:
  <https://devblogs.microsoft.com/directx/directstorage-1-4-release-adds-support-for-zstandard/>
- Xbox GDK DirectStorage overview:
  <https://learn.microsoft.com/gaming/gdk/docs/features/console/storage/directstorage/directstorage-overview>
- OpenPBR releases and changelog:
  <https://github.com/AcademySoftwareFoundation/OpenPBR/releases>

## C++ and toolchains

- C++23 compiler support:
  <https://en.cppreference.com/w/cpp/compiler_support/23>
- libc++ C++23 implementation status:
  <https://libcxx.llvm.org/Status/Cxx23.html>
- Standard feature-test macros:
  <https://en.cppreference.com/w/cpp/feature_test>
- P2996 static reflection:
  <https://wg21.link/P2996>
- WG21 feature-test recommendations for reflection:
  <https://wg21.link/P3394>
- C++26 contracts proposal:
  <https://wg21.link/P2900>
- `mdspan` specification (element access preconditions; no default bounds check):
  <https://wg21.link/P0009>
- `constexpr` mathematical functions:
  <https://wg21.link/P1383>
- C++ coroutine language support and frame lifetime:
  <https://en.cppreference.com/w/cpp/language/coroutines>
- EASTL upstream repository and allocator/container declarations:
  <https://github.com/electronicarts/EASTL>

Console compiler and standard-library support is determined by the installed SDK, not by the upstream Clang/MSVC/GCC version alone.

## Tooling, interop, and validation

- Microsoft native interoperability best practices:
  <https://learn.microsoft.com/dotnet/standard/native-interop/best-practices>
- .NET `SafeHandle` guidance:
  <https://learn.microsoft.com/dotnet/api/system.runtime.interopservices.safehandle>
- DXC command-line reference (`-Zpr`, SPIR-V and validation options):
  <https://github.com/microsoft/DirectXShaderCompiler/wiki/DXC-Command-Line>
- Clang AddressSanitizer:
  <https://clang.llvm.org/docs/AddressSanitizer.html>
- Clang ThreadSanitizer:
  <https://clang.llvm.org/docs/ThreadSanitizer.html>

## Physics and managed runtimes

- Jolt build and cross-platform determinism options:
  <https://github.com/jrouwe/JoltPhysics/blob/master/Build/README.md>
- NVIDIA PhysX SDK documentation:
  <https://nvidia-omniverse.github.io/PhysX/physx/latest/>
- Unity IL2CPP scripting backend:
  <https://docs.unity3d.com/6000.0/Documentation/Manual/scripting-backends-il2cpp.html>

## Platform-public information

- Nintendo Switch 2 technical specifications:
  <https://www.nintendo.com/us/gaming-systems/switch-2/tech-specs/>
- NVIDIA Switch 2 architecture overview:
  <https://blogs.nvidia.com/blog/nintendo-switch-2-leveled-up-with-nvidia-ai-powered-dlss-and-4k-gaming/>

Exact console APIs, memory reservations, certification requirements, decompression formats, and performance behavior must be checked against the current NDA SDK documentation.
