import Foundation
import Testing
@testable import CornettaCore

struct UpdateFeedSignatureTests {
    private let publicKey = "BCcSn9flFlqQeVWQqoM9iFr8xKhtsy5juX9CJO70Or3aPgQVJyZOfnWeJTTYImxkxm9U20bgDWVqM5BO/NNvi60="
    private let feed = Data(#"{"schema":1,"version":"0.0.0","release_url":"https://github.com/VVG-web/cornetta-en/releases/tag/v0.0.0"}"#.utf8)
    private let signature = "JSlfYFRdrcwOEm91R0QgtZVMglSm9pK+DoVdk+UfX872He6TEEpUQkCPn65rbz1q7OucF47Su+oiNg1Xl1vRiQ=="

    @Test func acceptsTheSignedFixture() {
        #expect(UpdateFeedSignature.verify(feed: feed, signatureBase64: signature, publicKeyBase64: publicKey))
    }

    @Test func rejectsChangedFeedOrSignature() {
        var changed = feed
        changed.append(0x20)
        #expect(!UpdateFeedSignature.verify(feed: changed, signatureBase64: signature, publicKeyBase64: publicKey))
        #expect(!UpdateFeedSignature.verify(feed: feed, signatureBase64: signature.dropLast() + "A", publicKeyBase64: publicKey))
    }

    @Test func rejectsMalformedKeysAndSignatures() {
        #expect(!UpdateFeedSignature.verify(feed: feed, signatureBase64: "", publicKeyBase64: publicKey))
        #expect(!UpdateFeedSignature.verify(feed: feed, signatureBase64: signature, publicKeyBase64: ""))
        #expect(!UpdateFeedSignature.verify(feed: feed, signatureBase64: Data(repeating: 0, count: 64).base64EncodedString(),
                                            publicKeyBase64: publicKey))
    }
}
