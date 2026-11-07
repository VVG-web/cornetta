import Testing
@testable import CornettaCore

struct ReleaseVersionTests {
    @Test func normalizesTags() {
        #expect(ReleaseVersion.normalized("v0.6.0") == "0.6.0")
        #expect(ReleaseVersion.normalized("0.6") == "0.6.0")
        #expect(ReleaseVersion.normalized("V1.2.3") == "1.2.3")
        #expect(ReleaseVersion.normalized("0.6.0-beta") == "0.6.0")
        #expect(ReleaseVersion.normalized("non-una-versione") == nil)
        #expect(ReleaseVersion.normalized("1.2.3.4") == nil)
    }

    @Test func comparesNumericComponents() {
        #expect(ReleaseVersion.isNewer("v0.6.0", than: "0.5.1"))
        #expect(ReleaseVersion.isNewer("0.5.10", than: "0.5.9"))
        #expect(ReleaseVersion.isNewer("1.0", than: "0.9.9"))
        #expect(!ReleaseVersion.isNewer("0.5.1", than: "v0.5.1"))
        #expect(!ReleaseVersion.isNewer("0.5.0", than: "0.5.1"))
        #expect(!ReleaseVersion.isNewer("non-una-versione", than: "0.5.1"))
    }
}
