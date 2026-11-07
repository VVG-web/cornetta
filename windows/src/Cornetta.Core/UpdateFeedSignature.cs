using System;
using System.Linq;
using System.Security.Cryptography;

namespace Cornetta.Core
{
    /// <summary>
    /// Verifica la firma ECDSA P-256 SHA-256 del feed aggiornamenti.
    /// La firma è r||s in base64 (64 byte). La chiave pubblica è il punto X9.63 non compresso
    /// in base64 (65 byte, il primo è 0x04). Una firma non valida non deve mai produrre una versione.
    /// </summary>
    public static class UpdateFeedSignature
    {
        public static bool Verify(byte[] feed, string signatureBase64, string publicKeyBase64)
        {
            try
            {
                byte[] point = Convert.FromBase64String((publicKeyBase64 ?? "").Trim());
                byte[] signature = Convert.FromBase64String((signatureBase64 ?? "").Trim());
                if (point.Length != 65 || point[0] != 0x04 || signature.Length != 64) return false;
                var parameters = new ECParameters
                {
                    Curve = ECCurve.NamedCurves.nistP256,
                    Q = new ECPoint
                    {
                        X = point.Skip(1).Take(32).ToArray(),
                        Y = point.Skip(33).Take(32).ToArray(),
                    },
                };
                using (var ecdsa = ECDsa.Create())
                {
                    ecdsa.ImportParameters(parameters);
                    return ecdsa.VerifyData(feed, signature, HashAlgorithmName.SHA256);
                }
            }
            catch (Exception ex) when (ex is FormatException || ex is CryptographicException
                || ex is PlatformNotSupportedException || ex is ArgumentException)
            {
                return false;
            }
        }
    }
}
