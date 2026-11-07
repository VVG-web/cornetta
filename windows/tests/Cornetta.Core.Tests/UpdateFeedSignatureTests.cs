using System;
using System.Text;
using Cornetta.Core;
using Xunit;

namespace Cornetta.Core.Tests
{
    public class UpdateFeedSignatureTests
    {
        private const string PublicKey = "BCcSn9flFlqQeVWQqoM9iFr8xKhtsy5juX9CJO70Or3aPgQVJyZOfnWeJTTYImxkxm9U20bgDWVqM5BO/NNvi60=";
        private const string Feed = "{\"schema\":1,\"version\":\"0.0.0\",\"release_url\":\"https://github.com/VVG-web/cornetta-en/releases/tag/v0.0.0\"}";
        private const string Signature = "JSlfYFRdrcwOEm91R0QgtZVMglSm9pK+DoVdk+UfX872He6TEEpUQkCPn65rbz1q7OucF47Su+oiNg1Xl1vRiQ==";

        [Fact]
        public void AcceptsTheSignedFixture()
        {
            Assert.True(UpdateFeedSignature.Verify(Encoding.UTF8.GetBytes(Feed), Signature, PublicKey));
        }

        [Fact]
        public void RejectsChangedFeedOrSignature()
        {
            Assert.False(UpdateFeedSignature.Verify(Encoding.UTF8.GetBytes(Feed + " "), Signature, PublicKey));
            Assert.False(UpdateFeedSignature.Verify(Encoding.UTF8.GetBytes(Feed),
                Signature.Substring(0, Signature.Length - 2) + "AA", PublicKey));
        }

        [Fact]
        public void RejectsMalformedKeysAndSignatures()
        {
            Assert.False(UpdateFeedSignature.Verify(Encoding.UTF8.GetBytes(Feed), "", PublicKey));
            Assert.False(UpdateFeedSignature.Verify(Encoding.UTF8.GetBytes(Feed), Signature, ""));
            Assert.False(UpdateFeedSignature.Verify(Encoding.UTF8.GetBytes(Feed),
                Convert.ToBase64String(new byte[64]), PublicKey));
        }
    }
}
