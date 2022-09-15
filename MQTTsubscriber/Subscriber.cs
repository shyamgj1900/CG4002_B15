using System;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using MQTTnet;
using MQTTnet.Client;
using MQTTnet.Packets;
using MQTTnet.Protocol;

namespace MQTTsubscriber
{
    class Subscriber
    {
        static async Task Main(string[] args)
        {
            var mqttFactory = new MqttFactory();
            var message = "";

            using (IMqttClient mqttClient = mqttFactory.CreateMqttClient())
            {
                var mqttClientOptions = new MqttClientOptionsBuilder()
                    .WithCredentials("cg4002_b15", "CG4002_B15")
                    .WithTcpServer("b1386744d1594b29a88d72d9bab70fbe.s1.eu.hivemq.cloud", 8883)
                    .WithTls()
                    .WithCleanSession()
                    .Build();

                Console.WriteLine("Finished auth");

                mqttClient.ApplicationMessageReceivedAsync += async e =>
                {
                    message = Encoding.UTF8.GetString(e.ApplicationMessage.Payload);
                    Console.WriteLine($"Received application message. -> {message}");

                    if (message == "grenade")
                    {
                        await PublishMessageasync(mqttClient);
                    }
                };

                var response = await mqttClient.ConnectAsync(mqttClientOptions, CancellationToken.None);
                Console.WriteLine(response);

                var mqttSubscribeOptions = mqttFactory.CreateSubscribeOptionsBuilder()
                    .WithTopicFilter(f => { f.WithTopic("Ultra96/visualizer/receive"); })
                    .Build();

                await mqttClient.SubscribeAsync(mqttSubscribeOptions, CancellationToken.None);

                Console.WriteLine("MQTT client subscribed to topic.");


                Console.WriteLine("Press enter to exit.");
                Console.ReadLine();
            }
        }

        private static async Task PublishMessageasync(IMqttClient client)
        {
            Random rnd = new Random();
            var idx = rnd.Next(0, 2);
            string[] payload = new string[] {"yes", "no"};
            var message = new MqttApplicationMessageBuilder()
                .WithTopic("Ultra96/visualizer/send")
                .WithQualityOfServiceLevel(MqttQualityOfServiceLevel.AtLeastOnce)
                .WithPayload(payload[idx])
                .Build();

            if (client.IsConnected)
            {
                await client.PublishAsync(message);
            }
        }
    }
}

