# RE-WORKER
Worker parent code for for our new [release engine hotness](https://github.com/RHInception/?query=re-).

This library provides a simple base for release engine workers to build from.

[![Build Status](https://api.travis-ci.org/RHInception/re-worker.png)](https://travis-ci.org/RHInception/re-worker/)

## Implementing
To implement a worker subclass off of **reworker.worker.Worker** and override the **process** method.

Worker also provides a few convenience methods to simplify use:

### Worker.send
Sends a message.

* **Inputs**:
 * topic: the routing key
 * body: the dict or list to send as the body
* **Returns**: None

### Worker.ack
Acks a message.

* **Inputs**:
 * basic\_deliver: pika.Spec.Basic.Deliver instance
* **Returns**: None

### Worker.run\_forever
Starts the main loop.

* **Inputs**: None
* **Returns**: None

### Worker.process
What a worker should do when a message is received. All output
should be written to the output logger.

* **Inputs**:
 * channel: pika.channel.Channel instance
 * basic\_deliver: pika.Spec.Basic.Deliver instance
 * properties: pika.Spec.BasicProperties instance (ex: headers)
 * body: dict or list that was json loaded off the message
 * output: logger instance to send output
* **Returns**: None


```python
from reworker.worker import Worker

class IPrintStuff(Worker):

    def process(self, channel, basic_deliver, properties, body, output):
        print body  # This is a loaded json structure
        output.info(str(body))  # output is the logger for process output
        self.ack(basic_deliver) # ack at the end


mq_conf = {....}
worker = IPrintStuff(mq_conf, 'myqueue', '/tmp/logs/')
worker.run_forever()
```

For a more in-depth example see the examples/ folder.
