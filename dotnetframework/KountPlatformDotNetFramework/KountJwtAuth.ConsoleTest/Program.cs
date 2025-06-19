using System;
using System.Net.Http;
using KountJwtAuth;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)    {
        try
        {
            //Console.WriteLine("Client ID: " + Environment.GetEnvironmentVariable("KOUNT_CLIENT_ID"));
            //Console.WriteLine("API Key: " + Environment.GetEnvironmentVariable("KOUNT_API_KEY"));

            var httpClient = new HttpClient();
            var tokenService = new TokenService(httpClient);
            var token = await tokenService.GetValidTokenAsync();

            Console.WriteLine("JWT:");
            Console.WriteLine(token);
        }
        catch (Exception ex)
        {
            Console.WriteLine("Token fetch failed:");
            Console.WriteLine(ex.Message);
        }
    }
}
