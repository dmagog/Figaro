FROM rabbitmq

RUN rabbitmq-plugins enable --offline rabbitmq_management rabbitmq_mqtt rabbitmq_federation_management rabbitmq_stomp

COPY rabbitmq.conf /etc/rabbitmq/rabbitmq.conf