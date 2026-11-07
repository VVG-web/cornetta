import CryptoKit
import Foundation

/// Verifica la firma ECDSA P-256 SHA-256 del feed aggiornamenti.
/// La firma è r||s in base64 (64 byte). La chiave pubblica è il punto X9.63 non compresso
/// in base64 (65 byte, il primo è 0x04). Una firma non valida non deve mai produrre una versione.
public enum UpdateFeedSignature {
    public static func verify(feed: Data, signatureBase64: String, publicKeyBase64: String) -> Bool {
        let signatureText = signatureBase64.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let signatureData = Data(base64Encoded: signatureText), signatureData.count == 64,
              let keyData = Data(base64Encoded: publicKeyBase64), keyData.count == 65, keyData.first == 0x04 else {
            return false
        }
        do {
            // CryptoKit accetta il punto X||Y senza il prefisso 0x04, mentre il feed usa X9.63.
            let key = try P256.Signing.PublicKey(rawRepresentation: keyData.dropFirst())
            let signature = try P256.Signing.ECDSASignature(rawRepresentation: signatureData)
            return key.isValidSignature(signature, for: feed)
        } catch {
            return false
        }
    }
}
