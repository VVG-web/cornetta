import Foundation

/// Confronto fra il tag di una release GitHub e la versione dell'app.
/// Accetta il prefisso «v» e fino a tre numeri: «v0.6.0», «0.6», «0.6.0».
/// Un valore che non è una versione resta nullo: meglio dire che il controllo è fallito
/// che annunciare un aggiornamento inesistente.
public enum ReleaseVersion {
    /// La versione normalizzata a tre numeri, senza prefisso «v», oppure nil.
    public static func normalized(_ raw: String) -> String? {
        guard let parts = components(raw) else { return nil }
        return parts.map(String.init).joined(separator: ".")
    }

    /// Vero se `candidate` è una versione successiva a `current`.
    public static func isNewer(_ candidate: String, than current: String) -> Bool {
        guard let left = components(candidate), let right = components(current) else { return false }
        for index in 0..<3 where left[index] != right[index] {
            return left[index] > right[index]
        }
        return false
    }

    private static func components(_ raw: String) -> [Int]? {
        var text = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.first == "v" || text.first == "V" {
            text.removeFirst()
        }
        let core = text.split(separator: "-", maxSplits: 1, omittingEmptySubsequences: false)[0]
        let fields = core.split(separator: ".", omittingEmptySubsequences: false)
        guard (1...3).contains(fields.count), fields.allSatisfy({ !$0.isEmpty && $0.allSatisfy(\.isNumber) }) else {
            return nil
        }
        var values = fields.compactMap { Int($0) }
        guard values.count == fields.count, values.allSatisfy({ $0 >= 0 }) else { return nil }
        while values.count < 3 { values.append(0) }
        return values
    }
}
