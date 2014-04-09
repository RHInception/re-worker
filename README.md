# RE-WORKER
Worker parent code for release engine workers.

# Rough Example
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
