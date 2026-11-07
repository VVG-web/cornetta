using Cornetta.Core;
using Xunit;

namespace Cornetta.Core.Tests
{
    public class ReleaseVersionTests
    {
        [Theory]
        [InlineData("v0.6.0", "0.6.0")]
        [InlineData("0.6", "0.6.0")]
        [InlineData("V1.2.3", "1.2.3")]
        [InlineData("0.6.0-beta", "0.6.0")]
        public void NormalizesTags(string raw, string expected)
        {
            Assert.Equal(expected, ReleaseVersion.Normalized(raw));
        }

        [Theory]
        [InlineData("non-una-versione")]
        [InlineData("1.2.3.4")]
        [InlineData("")]
        public void RejectsInvalidTags(string raw)
        {
            Assert.Null(ReleaseVersion.Normalized(raw));
        }

        [Theory]
        [InlineData("v0.6.0", "0.5.1", true)]
        [InlineData("0.5.10", "0.5.9", true)]
        [InlineData("1.0", "0.9.9", true)]
        [InlineData("0.5.1", "v0.5.1", false)]
        [InlineData("0.5.0", "0.5.1", false)]
        [InlineData("non-una-versione", "0.5.1", false)]
        public void ComparesNumericComponents(string candidate, string current, bool expected)
        {
            Assert.Equal(expected, ReleaseVersion.IsNewer(candidate, current));
        }
    }
}
