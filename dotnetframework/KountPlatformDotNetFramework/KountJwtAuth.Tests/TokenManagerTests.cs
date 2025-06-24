using System;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using KountJwtAuth;

namespace KountJwtAuth.Tests
{
    [TestClass]
    public class TokenManagerTests
    {
        [TestMethod]
        public void SetAccessToken_ShouldStoreTokenAndExpiration()
        {
            // Arrange
            var token = "test-token";
            var expiration = DateTime.UtcNow.AddMinutes(10);
            var manager = TokenManager.Instance;

            // Act
            manager.SetAccessToken(token, expiration);

            // Assert
            Assert.AreEqual(token, manager.GetAccessToken());
            Assert.AreEqual(expiration, manager.GetExpiration());
        }

        [TestMethod]
        public void IsTokenNearExpiry_ShouldReturnTrue_WhenNearExpiration()
        {
            // Arrange
            var manager = TokenManager.Instance;
            var soon = DateTime.UtcNow.AddMinutes(1);
            manager.SetAccessToken("short-life", soon);

            // Act
            var result = manager.IsTokenNearExpiry(TimeSpan.FromMinutes(2));

            // Assert
            Assert.IsTrue(result);
        }

        [TestMethod]
        public void IsTokenNearExpiry_ShouldReturnFalse_WhenFarFromExpiration()
        {
            // Arrange
            var manager = TokenManager.Instance;
            var far = DateTime.UtcNow.AddMinutes(10);
            manager.SetAccessToken("long-life", far);

            // Act
            var result = manager.IsTokenNearExpiry(TimeSpan.FromMinutes(2));

            // Assert
            Assert.IsFalse(result);
        }
    }
}