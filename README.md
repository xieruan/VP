## V2Ray Plugin For V2Board

### 安装

1. 下载

   ```bash
   git clone https://github.com/thank243/V2Board_Plugin.git
   ```

2. 安装依赖

   ```bash
   pip3 install grpcio google-api-python-client
   ```


### 使用

1. 增加执行权限

   ```bash
   chmod +x main.py v2ray -R
   ```
   
2. 修改cfg.json中的内容
    ```bash
   cp cfg.example.json cfg.json
   vi cfg.json
    ```

3. 运行程序
   ```bash
   ./main.py
   ```
4. 日志等级
    ```bash
   critical, error, warning, info, debug
    ```
5. 更新
    ```bash
    bash update.sh
    ```
    
    
### 其他

1. 审计

   直接面板添加，如何使用参考v2board及v2ray官方wiki。


2. 流量控制

   内置的没有直接系统设置的好用，具体资料参考
   https://github.com/ForgotFun/QosDocs
