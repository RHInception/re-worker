# RE-WORKER
Worker parent code for release engine workers.

# Rough Example
```python

from reworker.worker import Worker

class IPrintStuff(Worker):

    def process(self, channel, basic_deliver, properties, body):
        print body
        self.ack(basic_deliver)


mq_conf = {....}
worker = IPrintStuff(mq_conf, 'myqueue')
worker.run_forever()
```
