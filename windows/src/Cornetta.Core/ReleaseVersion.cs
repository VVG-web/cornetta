using System;
using System.Globalization;
using System.Linq;

namespace Cornetta.Core
{
    /// <summary>
    /// Confronto fra il tag di una release GitHub e la versione dell'app.
    /// Accetta il prefisso «v» e fino a tre numeri: «v0.6.0», «0.6», «0.6.0».
    /// Un valore che non è una versione resta nullo: meglio dire che il controllo è fallito
    /// che annunciare un aggiornamento inesistente.
    /// </summary>
    public static class ReleaseVersion
    {
        /// <summary>La versione normalizzata a tre numeri, senza prefisso «v», oppure null.</summary>
        public static string? Normalized(string raw)
        {
            int[]? parts = Components(raw);
            return parts == null ? null : string.Join(".", parts.Select(p => p.ToString(CultureInfo.InvariantCulture)));
        }

        /// <summary>Vero se <paramref name="candidate"/> è una versione successiva a <paramref name="current"/>.</summary>
        public static bool IsNewer(string candidate, string current)
        {
            int[]? left = Components(candidate);
            int[]? right = Components(current);
            if (left == null || right == null) return false;
            for (int i = 0; i < 3; i++)
            {
                if (left[i] != right[i]) return left[i] > right[i];
            }
            return false;
        }

        private static int[]? Components(string raw)
        {
            string text = (raw ?? "").Trim();
            if (text.StartsWith("v", StringComparison.OrdinalIgnoreCase)) text = text.Substring(1);
            int dash = text.IndexOf('-');
            if (dash >= 0) text = text.Substring(0, dash);
            string[] fields = text.Split('.');
            if (fields.Length < 1 || fields.Length > 3) return null;
            var values = new int[fields.Length];
            for (int i = 0; i < fields.Length; i++)
            {
                if (fields[i].Length == 0 || !fields[i].All(char.IsDigit)) return null;
                if (!int.TryParse(fields[i], NumberStyles.None, CultureInfo.InvariantCulture, out values[i])) return null;
            }
            var result = new int[3];
            Array.Copy(values, result, values.Length);
            return result;
        }
    }
}
