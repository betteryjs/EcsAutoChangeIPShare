#!/usr/bin/bash

systemctl stop EcsTGBot.service
echo  "" > AliCloud-HK-ECS.log

cp  EcsTGBot.service  /lib/systemd/system/
chmod 644 /lib/systemd/system/EcsTGBot.service
systemctl daemon-reload
systemctl start EcsTGBot.service
systemctl enable EcsTGBot.service
systemctl status EcsTGBot.service
tail -f AliCloud-HK-ECS.log