## On-line магазин пиццы в виде бота Telegram
#### Пример работающего бота: [Bot](https://t.me/pizza_sergryap_bot)

![animation1](https://user-images.githubusercontent.com/99894266/210982091-844ba29f-75d2-4629-a7a9-06ea9fcbf685.gif)


Интернет магазин создан на базе API сервиса [Moltin](https://www.moltin.com/).

В представленной программе реализованы основные методы взаимодействия покупателя с магазином:

* просмотр списка доступных товаров
* просмотр информации о конкретном товаре
* возможность добавить товар в корзину или удалить из неё
* просмотр корзины
* оплата товаров в корзине
* создание заказа в CMS магазина
* отправка данных о заказе доставщику пиццы
* добавление информации о покупателе в CMS магазина

### Из чего состоит программа:

* В модуле `api_store.py` реализованы функции для взаимодействия с API магазина

* В модуле `bot_tg.py` реализовано взаимодействие пользователя через интерфейс telegram с API магазина

* В модуле `logger.py` реализован класс собственного обработчика логов

* В модуле `geo_informer.py` реализованы функции получения данных о геолокации и расчета минимальных расстояний

* В модуле `upload_data.py` реализованы функции загрузки данных в CMS магазина


### Для работы бота необходимо создать файл .env в корневой директории проекта по шаблону:

```
TELEGRAM_TOKEN=<Токен от бота Tg>
TELEGRAM_TOKEN_LOG=<Токен от бота Tg для отправки сообщения логгера>
CHAT_ID_LOG=<Id чата для получения сообщений логгера>
CLIENT_ID=<Уникальный идентификатор клиента API магазина>
CLIENT_SECRET=<Секретный ключ клиента API магазина>
DATABASE_PASSWORD=<Пароль доступа к базе Redis>
DATABASE_HOST=<Хост от базы Redis>
DATABASE_PORT=<Порт базы Redis>
YANDEX_GEO_TOKEN=<Токен от API геокодера Яндекса>
PROVIDER_TOKEN=<Токен сервиса приема платежей>
```

### Порядок установки бота:

У вас должен быть установлен python версии не ниже 3.10.6
У вас должны быть установлены следующие пакеты: `git`, `python3-pip`, `python3-venv`

1. Загрузите данные:

```sh
git clone git@github.com:Sergryap/pizza-payments.git
```

2. Перейдите в созданную директорию:

```sh
cd pizza-payments-shop
```

3. В корневой папке проекта создайте файл .env по описанию выше:

```sh
sudo nano .env
```

4. Находясь в корневой папке проекта, создайте виртуальное окружение:

```sh
python3 -m venv venv
```

5. Активируйте созданное виртуальное окружение:

```sh
source venv/bin/activate
```

6. Установите необходимые библиотеки:

```sh
pip install -r requirements.txt
```
![Снимок экрана от 2023-01-06 13-37-03](https://user-images.githubusercontent.com/99894266/210973167-ba176515-5f1e-4725-a289-60b012ff0e59.png)

![Снимок экрана от 2023-01-06 13-38-25](https://user-images.githubusercontent.com/99894266/210973282-e5198a39-adc7-4f53-b7c2-93573cc18b30.png)

7. Запустите бота:

```sh
python3 bot_tg.py
```

## Как установить бота для Facebook

Бот facebook реализован в модуле fb_bot.py посредством технологии webhook.

### Для запуска webhook (специального сайта на который приходят события от api facebook) выполните следующее:
1. Установите nginx на своем удаленном сервере и пропишите в его настройках следующую конфигурацию:
```
server {
        location /images/ {
                alias /opt/facebook-bot-webhook/images/;
        }      
        location / {
                 include '/etc/nginx/proxy_params';
                 proxy_pass http://127.0.0.1:8003/;
        }

	  root /var/www/html;
    server_name starburger-serg.store;
    listen [::]:443 ssl ipv6only=on;
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/starburger-serg.store/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/starburger-serg.store/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

}
server {
    if ($host = starburger-serg.store) {
        return 301 https://$host$request_uri;
    }
    
	listen 80 ;
	listen [::]:80 ;
    server_name starburger-serg.store;
    return 404;
}
```
При этом замените название домена на своё

2. Настройте автоматическое обновление сертификатов для домена, создав два файла:

certbot-renewal.service:
```
[Unit]
Description=Certbot Renewal

[Service]
ExecStart=/usr/bin/certbot renew --force-renewal --post-hook "systemctl reload nginx.service"
```
certbot-renewal.timer:
```
[Unit]
Description=Timer for Certbot Renewal

[Timer]
OnBootSec=300
OnUnitActiveSec=1w

[Install]
WantedBy=multi-user.target
```
3. Настройте автоматический запуск webhook:

Для этого создайте файл `/etc/systemd/system/facebook-bot-webhook.service`:
```
[Unit]
Description=fb-webhook-site

[Service]
Type=simple
WorkingDirectory=/opt/facebook-bot-webhook
EnvironmentFile=/opt/facebook-bot-webhook/.env
ExecStart=/opt/facebook-bot-webhook/venv/bin/gunicorn -w 3 -b 127.0.0.1:8003 fb_bot:app
Restart=always

[Install]
WantedBy=multi-user.target
```

4. В файл `.env` добавьте значения переменных:

```
HIERARCHY_ID=<HIERARCHY ID от магазина moltin>
FRONT_PAGE_NODE_ID=<NODE ID от вашего основного node для главного меню>
PAGE_ACCESS_TOKEN=<Токен от вашего приложения facebook>
VERIFY_TOKEN=<токен для верификации webhook - произвольная строка>
```

5. Запустите бота, выполнив команды

```
systemctl daemon-reload
systemctl start facebook-bot-webhook.service
systemctl enable facebook-bot-webhook.service 
```

#### Ссылка на fb приложение с ботом:
[fb-pizza-bot](https://www.facebook.com/profile.php?id=100089995515393)
