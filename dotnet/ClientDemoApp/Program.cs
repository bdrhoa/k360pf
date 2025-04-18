// Program.cs
using System;
using System.IO;
using System.Threading.Tasks;
using KountJwtAuth.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Polly;
using Polly.Extensions.Http;

namespace ClientDemoApp
{
    internal class Program
    {
        public static async Task Main(string[] args)
        {
            var host = Host.CreateDefaultBuilder(args)
                .ConfigureAppConfiguration((context, config) =>
                {
                    config.SetBasePath(Directory.GetCurrentDirectory());
                    config.AddJsonFile("appsettings.json", optional: false, reloadOnChange: true);
                })
                .ConfigureServices((context, services) =>
                {
                    services.AddLogging(configure => configure.AddConsole());

                    services.AddHttpClient<TokenService>()
                        .AddPolicyHandler(HttpPolicyExtensions
                            .HandleTransientHttpError()
                            .WaitAndRetryAsync(3, retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt))));

                    services.AddSingleton(TokenManager.Instance);
                })
                .Build();

            var tokenService = host.Services.GetRequiredService<TokenService>();
            var token = await tokenService.GetValidTokenAsync();

            Console.WriteLine("Retrieved JWT Token:");
            Console.WriteLine(token);

            Console.WriteLine("Press Ctrl+C to exit. Token auto-refresh will continue to run in the background.");
            await Task.Delay(Timeout.Infinite);
        }
    }
}
