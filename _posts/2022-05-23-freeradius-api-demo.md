---
layout: post
title: Deploying a FastAPI based application for FreeRADIUS
subtitle: HTTP endpoints make life easier
comments: true
---

I've built a FastAPI app which you can run on your FreeRADIUS servers to handle the interaction between external scripts/os/bss and the database. This also includes returning data in a presentable format instead of having to correlate users and groups to specific attribute pairs stored in the radcheck/radreply/radgroupcheck/radgroupreply tables. (Also endpoints are available for accounting and postauth records)

There are some examples on the github project on how you would deploy this but in this demo, I will only be covering the 3rd option (but from a single VM perspective) where we will run the API as a docker container on the same VM which is running FreeRADIUS, however nothing is to stop you to deploy this API separately from the FreeRADIUS VM/containers.

## Installing FreeRADIUS

FreeRADIUS guides can be found everywhere online or assume that if you attempt to install it via your preferred package-manager that everything is up to date, in my lab I have installed this on Ubuntu 22.04 LTS.

```
sudo apt update
echo "deb http://packages.networkradius.com/freeradius-3.0/ubuntu/focal focal main" |     sudo tee /etc/apt/sources.list.d/networkradius.list > /dev/null
curl -s 'https://packages.networkradius.com/pgp/packages%40networkradius.com' |     sudo tee /etc/apt/trusted.gpg.d/packages.networkradius.com.asc > /dev null
sudo apt update
sudo apt install freeradius freeradius-mysql
```

Once this has installed, you can check the version by running: `freeradius -v`.
```
radiusd: FreeRADIUS Version 3.0.26, for host x86_64-pc-linux-gnu, built on Mar 23 2022 at 23:13:55
```

## Installing MariaDB

In this example, I will be using MariaDB and then add the minimal configuration to FreeRADIUS to get this API demo working however in production, you would want to validate your design and configuration to ensure module failover works with redundant database servers, ensure the correct modules in FreeRADIUS are enabled and any additional tweaks have been made.

```
sudo apt install mariadb-server
sudo mysql_secure_installation
```

After running through the installation, we can now proceed with creating our `radius` database and importing the schema provided by FreeRADIUS for MySQL which will create our relevant tables.

`sudo mariadb -u root -p`

1. Create the `radius` databaase

    ```
    CREATE DATABASE radius;
    ```

2. Create a database user which we will use during this demo, you should ensure database permissions are set correctly for a production environment!

    ```
    CREATE USER 'radius'@'localhost' IDENTIFIED by 'changemeP!z';
    GRANT ALL PRIVILEGES ON radius.* TO 'radius'@'localhost';
    FLUSH PRIVILEGES;
    ```

You will also need to add the user again with access from the IP(s) of the FreeRADIUS servers where the docker container will run on. However because we are running the API in a container, we will just allow % for the purpose of this demo.

    ```
    CREATE USER 'radius'@'%' IDENTIFIED by 'changemeP!z';
    GRANT ALL PRIVILEGES ON radius.* TO 'radius'@'%';
    FLUSH PRIVILEGES;
    ```

Ensure the bind-address in `/etc/mysql/mariadb.conf.d/50-server.cnf` also is set to allow remote connections.
    ```
    # Instead of skip-networking the default is now to listen only on
    # localhost which is more compatible and is not less secure.
    bind-address            = 0.0.0.0
    ```

3. Import the schema into the database 

    ```
    sudo su
    mysql -u root -p radius < /etc/freeradius/3.0/mods-config/sql/main/mysql/schema.sql
    ```

4. Ensure you can log in using the username/password created in step 2. Ensure that the following tables are created which means the schema.sql was successfully imported

    ```
    mysql -u radius -p

    MariaDB [(none)]> USE radius;
    MariaDB [radius]> SHOW TABLES;
    +------------------+
    | Tables_in_radius |
    +------------------+
    | nas              |
    | radacct          |
    | radcheck         |
    | radgroupcheck    |
    | radgroupreply    |
    | radpostauth      |
    | radreply         |
    | radusergroup     |
    +------------------+
    8 rows in set (0.000 sec)
    ```

## Configuring FreeRADIUS to use the database

There are a few initial steps we need to complete so that FreeRADIUS will use our database, firstly we will start with creating a symlink with the sql module and then configure that to point to our local database instance.

```
sudo ln -s /etc/freeradius/3.0/mods-available/sql /etc/freeradius/3.0/mods-enabled/
```

Now lets edit the sql module to include the details to connect to our local lab database.

```
vim /etc/freeradius/3.0/mods-enabled/sql

sql {
        dialect = "mysql"
        driver = "rlm_sql_${dialect}"
        server = "localhost"
        port = 3306
        login = "radius"
        password = "changemeP!z" # Update this to the password you set when creating the database user in step 2
        radius_db = "radius"
        acct_table1 = "radacct"
        acct_table2 = "radacct"
        postauth_table = "radpostauth"
        authcheck_table = "radcheck"
        groupcheck_table = "radgroupcheck"
        authreply_table = "radreply"
        groupreply_table = "radgroupreply"
        usergroup_table = "radusergroup"
        delete_stale_sessions = yes
        pool {
                start = 0
                min = ${thread[pool].min_spare_servers}
                max = ${thread[pool].max_servers}
                spare = ${thread[pool].max_spare_servers}
                uses = 0
                retry_delay = 30
                lifetime = 0
                idle_timeout = 60
        }
        read_clients = no
        client_table = "nas"
        group_attribute = "SQL-Group"
        $INCLUDE ${modconfdir}/${.:name}/main/${dialect}/queries.conf
}
```

If we stop the freeradius service, we can run it in debug mode to see what is happening when RADIUS access-request packets come into the server.

```
systemctl stop freeradius

freeradius -X
(10) Sent Access-Reject Id 98 from 10.4.20.89:1812 to 10.4.20.94:40130 length 86
(11) Sent Access-Reject Id 99 from 10.4.20.89:1812 to 10.4.20.94:40130 length 86
```

If you want freeradius to throw an error if the database is unreachable, you can change the `start` variable to `${thread[pool].num_workers}`. After running this, I have a Cisco XRv9K with a subscriber connected to an interface to get the router to send RADIUS access-request packets to my lab radius server. Now we can proceed to clone the project and run the API on our server, at this point I already have docker installed and won't go through the installation of this but you can find a lot of guides online. (https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-20-04)

1. Clone the project

    ```
    git clone https://github.com/BSpendlove/freeradius-api.git
    ```

2. Copy the .env-example to .env, and fill out some variables

    ```
    cp .env-example .env
    vim .env

    API_TOKEN_KEY=x-api-token
    API_TOKEN=change-me-please
    SQLALCHEMY_DATABASE_URL="mysql+pymysql://radius:changemeP!z@10.4.20.89:3006/radius?charset=utf8mb4"
    MONGODB_URI=mongodb://freeradius:changemeP!z@mongo:27017/
    ```

3. (Optional) Mount the FreeRADIUS shared dictionaries in the docker-compose.yml file if you want to test out the `validate_avpairs` option, this enables attribute lookup when you try to add it into the radcheck/radreply/radgroupcheck and radgroupreply database tables. If it isn't in your FreeRADIUS shared dictionaries then it will return a 404 error and not insert the attribute into the database. By default this is disabled and you can skip this optional step if you'd like...

    ```
    version: '3.1'

    services:
    freeradius_bng_api:
        build: .
        volumes:
        - /usr/share/freeradius/:/freeradius_dictionaries:ro # HERE
    ```

4. Run the docker-compose file (you can remove the MongoDB service if you skip step 3)

    ```
    cd ~/freeradius-api
    docker-compose up --build
    ```

Once this is finished, we should see the server start up:

```
freeradius_bng_api_1  | INFO:     Started server process [1]
freeradius_bng_api_1  | INFO:     Waiting for application startup.
freeradius_bng_api_1  | INFO:     Application startup complete.
freeradius_bng_api_1  | INFO:     Uvicorn running on http://0.0.0.0:80 (Press CTRL+C to quit)
```

We can now start sending API requests to the endpoint. Lets attempt to create a group:

```
brandon@labsql-1:~$ curl --location --request POST 'http://localhost:8083/api/v1/radius/groups/' \
--header 'x-api-token: change-me-please' \
--header 'Content-Type: application/json' \
--data-raw '{
    "groupname": "SPEED_150"
}'

REPLY:
{
   "groupname":"SPEED_150",
   "radgroupcheck":[
      {
         "attribute":"Cleartext-Password",
         "op":"=",
         "value":"default",
         "id":1
      }
   ],
   "radgroupreply":[
      
   ],
   "radusergroup":[
      
   ]
}
```

Let's create an attribute reply for this group, for example a policy-map that should be applied to a subscriber when the RADIUS Access-Accept is sent back.

```
curl --location --request POST 'http://localhost:8083/api/v1/radius/groups/SPEED_150/attribute/reply' \
--header 'x-api-token: change-me-please' \
--header 'Content-Type: application/json' \
--data-raw '{
    "attribute": "Cisco-AVPair",
    "op": "+=",
    "value": "subscriber:sub-qos-policy-in=PM_SPEED_150"
}'

REPLY:
{
   "groupname":"SPEED_150",
   "radgroupcheck":[
      {
         "attribute":"Cleartext-Password",
         "op":"=",
         "value":"default",
         "id":1
      }
   ],
   "radgroupreply":[
      {
         "attribute":"Cisco-AVPair",
         "op":"+=",
         "value":"subscriber:sub-qos-policy-in=PM_SPEED_150",
         "id":1
      }
   ],
   "radusergroup":[
      
   ]
}
```

## Creating a customer and assigning a speed package to be returned to a BNG

Let's create a "customer" (username) and assign them to the group `SPEED_150` that we created, we will then see if these attributes are returned in the RADIUS message sent back to our BNG in the lab. Currently I will authenticate a CSR1000V by the MAC address of `5000.0002.0000`.

Using the API endpoint, we can easily create a username who will be apart of the `SPEED_150` group that we created previously.

```
curl --location --request POST 'http://localhost:8083/api/v1/radius/users' \
--header 'x-api-token: change-me-please' \
--header 'Content-Type: application/json' \
--data-raw '{
    "username": "5000.0002.0000",
    "groupname": "SPEED_150"
}'

REPLY:
{
   "username":"5000.0002.0000",
   "radcheck":[
      
   ],
   "radreply":[
      
   ],
   "radusergroup":[
      {
         "groupname":"SPEED_150",
         "priority":"1"
      }
   ]
}
```

Time to see if this username is authorized and the relevant attributes added to the `SPEED_150` RADIUS group are appended to the RADIUS access-accept message.

```
(17) Received Access-Request Id 156 from 10.4.20.94:40130 to 10.4.20.89:1812 length 299
<...output omitted...>
(17) sql: SQL-User-Name set to '5000.0002.0000'
rlm_sql (sql): Reserved connection (14)
(17) sql: EXPAND SELECT id, username, attribute, value, op FROM radcheck WHERE username = '%{SQL-User-Name}' ORDER BY id
(17) sql:    --> SELECT id, username, attribute, value, op FROM radcheck WHERE username = '5000.0002.0000' ORDER BY id
(17) sql: Executing select query: SELECT id, username, attribute, value, op FROM radcheck WHERE username = '5000.0002.0000' ORDER BY id
(17) sql: WARNING: User not found in radcheck table.
(17) sql: EXPAND SELECT groupname FROM radusergroup WHERE username = '%{SQL-User-Name}' ORDER BY priority
(17) sql:    --> SELECT groupname FROM radusergroup WHERE username = '5000.0002.0000' ORDER BY priority
(17) sql: Executing select query: SELECT groupname FROM radusergroup WHERE username = '5000.0002.0000' ORDER BY priority
(17) sql: User found in the group table
(17) sql: EXPAND SELECT id, groupname, attribute, Value, op FROM radgroupcheck WHERE groupname = '%{SQL-Group}' ORDER BY id
(17) sql:    --> SELECT id, groupname, attribute, Value, op FROM radgroupcheck WHERE groupname = 'SPEED_150' ORDER BY id
(17) sql: Executing select query: SELECT id, groupname, attribute, Value, op FROM radgroupcheck WHERE groupname = 'SPEED_150' ORDER BY id
(17) sql: Group "SPEED_150": Conditional check items matched
(17) sql: Group "SPEED_150": Merging assignment check items
(17) sql:   Cleartext-Password := "default"
(17) sql: EXPAND SELECT id, groupname, attribute, value, op FROM radgroupreply WHERE groupname = '%{SQL-Group}' ORDER BY id
(17) sql:    --> SELECT id, groupname, attribute, value, op FROM radgroupreply WHERE groupname = 'SPEED_150' ORDER BY id
(17) sql: Executing select query: SELECT id, groupname, attribute, value, op FROM radgroupreply WHERE groupname = 'SPEED_150' ORDER BY id
(17) sql: Group "SPEED_150": Merging reply items
(17) sql:   Cisco-AVPair += "subscriber:sub-qos-policy-in=PM_SPEED_150"
<...output omitted...>
(17) Sent Access-Accept Id 156 from 10.4.20.89:1812 to 10.4.20.94:40130 length 69
(17)   Cisco-AVPair = "subscriber:sub-qos-policy-in=PM_SPEED_150"
(17) Finished request
```

We can check the postauth API endpoint to validate this Access-Accept ID, note that the ID in the debug menu is not at all related to the database ID:

```
curl --location --request GET 'http://localhost:8083/api/v1/radius/postauth/5000.0002.0000?limit=1' \ \
--header 'x-api-token: change-me-please'

REPLY:
[
   {
      "username":"5000.0002.0000",
      "reply":"Access-Accept",
      "authdate":"2022-05-23T22:16:10.135323",
      "id":56
   }
]
```

## Real world scenario

During the lab, I've been authenticating BNG subscribers to inherit a policy map template configured on the device, here you can see the radius attributes returned via the FreeRADIUS server, which the username/group and attributes were all created using these API endpoints.

```
RP/0/RP0/CPU0:BNG-1#show run policy-map PM_SPEED_150
Mon May 23 22:23:17.816 UTC
policy-map PM_SPEED_150
 class class-default
  police rate 165 mbps 
  ! 
 ! 
 end-policy-map
! 

RP/0/RP0/CPU0:BNG-1#show subscriber session all detail internal 
Mon May 23 22:25:37.161 UTC
Interface:                GigabitEthernet0/0/0/0.500.ip29
Circuit ID:               Unknown
Remote ID:                Unknown
Type:                     IP: DHCP-trigger
IPv4 State:               Up, Mon May 23 22:25:08 2022
IPv4 Address:             10.50.0.31, VRF: default # IP reachability
IPv4 Up helpers:          0x00000040 {IPSUB}
IPv4 Up requestors:       0x00000040 {IPSUB}
Mac Address:              5000.0002.0000
Account-Session Id:       040000ac
Nas-Port:                 Unknown
User name:                5000.0002.0000
Formatted User name:      5000.0002.0000
Client User name:         unknown
Outer VLAN ID:            501
Inner VLAN ID:            10
Subscriber Label:         0x0400002b
Created:                  Mon May 23 22:25:06 2022
State:                    Activated, Mon May 23 22:25:08 2022

Authentication:           unauthenticated
Authorization:            authorized # AUTHORIZED
Ifhandle:                 0x01000120
Session History ID:       11
Access-interface:         GigabitEthernet0/0/0/0.500
iEdge Oper Flags:         0x00000006
SRG Flags:                0x00000000(N)
SRG Group ID:             0
Prepaid State:            (Disabled)
Policy Executed: 

event Session-Start match-first [at 1653344706]
 class type control subscriber IPOE_DHCPV4V6 do-until-failure [Succeeded]
 1 authorize aaa list default [cerr: Success][aaa: Success]
 2 activate dynamic-template IPOE_DT [cerr: Success][aaa: Success]
Session Accounting:        
  Acct-Session-Id:          040000ac
  Method-list:              default
  Accounting started:       Mon May 23 22:25:08 2022
  Interim accounting:       On, interval 30 mins
    Last successful update: Never
    Last unsuccessful update: Never
    Next update in:         00:29:31 (dhms)
    Last update sent:       Never
    Updates sent:           0
    Updates accepted:       0
    Updates rejected:       0
    Update send failures:   0
Last COA request received: unavailable
User Profile received from AAA:
 Attribute List: 0x5586447cc358
1:  sub-qos-policy-in len= 12  value= PM_SPEED_150 # Applied via RADIUS
Services:
  Name        : IPOE_DT
  Service-ID  : 0x4000002
  Type        : Template
  Status      : Applied

```

If you are interested in trying out this API or are interested in it then feel free to check it out over on my Github page:
https://github.com/BSpendlove/freeradius-api

Over time I will be adding additional bits to this project and improving it as I go along however as of May 2022, this API works for the latest FreeRADIUS version and stops you having to add your own scripts to directly interact with the database or manually insert items via SQL. I am always open to suggestions and fixes so please do contact me if you think something can be improved!