using System;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using MQTTnet;
using MQTTnet.Client;
using MQTTnet.Packets;


namespace MQTTsubscriber
{
    class Subscriber
    {
        static async Task Main(string[] args)
        {
            var mqttFactory = new MqttFactory();

            using (var mqttClient = mqttFactory.CreateMqttClient())
            {
                var mqttClientOptions = new MqttClientOptionsBuilder()
                    .WithCredentials("cg4002_b15", "CG4002_B15")
                    .WithTcpServer("b1386744d1594b29a88d72d9bab70fbe.s1.eu.hivemq.cloud", 8883)
                    .WithTls()
                    .WithCleanSession()
                    .Build();

                Console.Write("Finished auth");
                
                mqttClient.ApplicationMessageReceivedAsync += e =>
                {
                    Console.WriteLine($"Received application message. -> {Encoding.UTF8.GetString(e.ApplicationMessage.Payload)}");
                    //e.DumpToConsole();

                    return Task.CompletedTask;
                };

                var response = await mqttClient.ConnectAsync(mqttClientOptions, CancellationToken.None);
                Console.WriteLine(response);

                var mqttSubscribeOptions = mqttFactory.CreateSubscribeOptionsBuilder()
                    .WithTopicFilter(f => { f.WithTopic("Ultra96/visualizer"); })
                    .Build();

                await mqttClient.SubscribeAsync(mqttSubscribeOptions, CancellationToken.None);

                Console.WriteLine("MQTT client subscribed to topic.");

                Console.WriteLine("Press enter to exit.");
                Console.ReadLine();
            }
        }
    }
}

