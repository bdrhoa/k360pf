using System;
using System.Net.Http;
using KountJwtAuth;
using System.Threading.Tasks;
using System.Threading;

class Program
{
    static async Task Main(string[] args)
    {
        try
        {
            var httpClient = new HttpClient();
            var tokenService = new TokenService(httpClient);
            string lastToken = string.Empty;

            while (true)
            {
                var token = await tokenService.GetValidTokenAsync();

                if (token != lastToken)
                {
                    Console.WriteLine($"{DateTime.UtcNow}: New JWT:");
                    Console.WriteLine(token);

                    var expiration = TokenManager.Instance.GetExpiration();
                    Console.WriteLine($"Token expires at UTC: {expiration}");

                    lastToken = token;
                }

                Thread.Sleep(TimeSpan.FromSeconds(30));
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine("Token fetch failed:");
            Console.WriteLine(ex.Message);
        }
    }
}