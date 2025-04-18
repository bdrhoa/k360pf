using System;
using KountJwtAuth.Services;
using Xunit;

namespace KountJwtAuth.Tests
{
    public class TokenManagerTests
    {
        [Fact]
        public void CanSetAndGetToken()
        {
            var token = "abc123";
            var expiration = DateTime.UtcNow.AddMinutes(10);

            var manager = TokenManager.Instance;
            manager.SetAccessToken(token, expiration);

            Assert.Equal(token, manager.GetAccessToken());
            Assert.False(manager.IsTokenNearExpiry(TimeSpan.FromMinutes(5)));
        }
    }
}