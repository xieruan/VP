## V2Ray Plugin For V2Board

### 安装
#### 环境需先安装python3 不想折腾的请到docker版 <a href="https://github.com/xieruan/vp-docker" target="_blank">传送门 </a>
1. 下载

   ```bash
   git clone https://github.com/xieruan/vp.git
   ```

2. 安装依赖

   ```bash
   pip3 install grpcio google-api-python-client loguru
   ```


### 使用

1. 增加执行权限

   ```bash
   chmod +x main.py v2ray/v2*
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

   直接面板添加，参考v2board及v2ray官方wiki。


2. 流量控制

   参考
   https://github.com/ForgotFun/QosDocs
