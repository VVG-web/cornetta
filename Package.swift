// swift-tools-version:5.10
import PackageDescription

let package = Package(
    name: "Cornetta",
    platforms: [.macOS("14.4")],
    products: [
        .executable(name: "Cornetta", targets: ["Cornetta"]),
    ],
    targets: [
        .target(name: "CornettaCore"),
        .executableTarget(
            name: "Cornetta",
            dependencies: ["CornettaCore"],
            exclude: ["Resources"],
            linkerSettings: [.unsafeFlags(["-Xlinker", "-rpath", "-Xlinker", "@executable_path/../Frameworks"])]
        ),
        .testTarget(name: "CornettaCoreTests", dependencies: ["CornettaCore"]),
    ]
)
