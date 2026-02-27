#!/usr/bin/env bash
#
# AI Quant System — 一键服务器部署脚本
#
# 用法:
#   chmod +x deploy.sh
#   ./deploy.sh              # 交互式部署 (推荐)
#   ./deploy.sh docker       # Docker 模式
#   ./deploy.sh bare         # 裸机模式
#   ./deploy.sh update       # 更新 (git pull + 重建)
#   ./deploy.sh stop         # 停止服务
#   ./deploy.sh status       # 查看状态
#   ./deploy.sh logs         # 查看日志
#
set -euo pipefail

# ============ 颜色 ============
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }
title() { echo -e "\n${CYAN}━━━ $* ━━━${NC}\n"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ============ 环境检测 ============
check_command() {
    command -v "$1" &>/dev/null
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        echo "$ID"
    elif [[ "$(uname)" == "Darwin" ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

# ============ 配置 .env ============
setup_env() {
    title "配置环境变量"

    if [[ -f .env ]]; then
        warn ".env 文件已存在"
        read -rp "是否重新配置? (y/N): " redo
        [[ "$redo" != "y" && "$redo" != "Y" ]] && return 0
    fi

    cp .env.example .env

    echo ""
    info "请输入配置信息 (直接回车使用默认值):"
    echo ""

    # Supabase
    read -rp "  Supabase URL [已有默认值]: " val
    [[ -n "$val" ]] && sed -i "s|SUPABASE_URL=.*|SUPABASE_URL=$val|" .env

    read -rp "  Supabase Anon Key [已有默认值]: " val
    [[ -n "$val" ]] && sed -i "s|SUPABASE_KEY=.*|SUPABASE_KEY=$val|" .env

    # DeepSeek
    read -rp "  DeepSeek API Key (留空跳过): " val
    if [[ -n "$val" ]]; then
        sed -i "s|DEEPSEEK_API_KEY=.*|DEEPSEEK_API_KEY=$val|" .env
    fi

    # Secret
    SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "change-me-$(date +%s)")
    sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET|" .env

    # Production settings
    sed -i "s|DEBUG=.*|DEBUG=false|" .env

    info ".env 配置完成"
}

# ============ Docker 部署 ============
deploy_docker() {
    title "Docker 模式部署"

    # 检测 Docker
    if ! check_command docker; then
        warn "未检测到 Docker，正在安装..."
        install_docker
    fi

    if ! check_command docker-compose && ! docker compose version &>/dev/null; then
        warn "未检测到 docker-compose，正在安装..."
        install_docker_compose
    fi

    # 确定 compose 命令
    if docker compose version &>/dev/null; then
        COMPOSE="docker compose"
    else
        COMPOSE="docker-compose"
    fi

    setup_env

    title "构建镜像"
    $COMPOSE build --no-cache

    title "启动服务"
    $COMPOSE up -d

    echo ""
    info "部署完成!"
    show_endpoints
}

install_docker() {
    local os=$(detect_os)
    case "$os" in
        ubuntu|debian)
            sudo apt-get update -qq
            sudo apt-get install -y -qq ca-certificates curl gnupg
            sudo install -m 0755 -d /etc/apt/keyrings
            curl -fsSL "https://download.docker.com/linux/$os/gpg" | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null
            sudo chmod a+r /etc/apt/keyrings/docker.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$os $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            sudo apt-get update -qq
            sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
            sudo usermod -aG docker "$USER" || true
            ;;
        centos|rhel|fedora|almalinux|rocky)
            sudo yum install -y yum-utils
            sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            sudo systemctl enable --now docker
            sudo usermod -aG docker "$USER" || true
            ;;
        *)
            err "无法自动安装 Docker，请手动安装: https://docs.docker.com/get-docker/"
            exit 1
            ;;
    esac
    info "Docker 安装完成"
}

install_docker_compose() {
    sudo curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    info "docker-compose 安装完成"
}

# ============ 裸机部署 ============
deploy_bare() {
    title "裸机模式部署"
    local os=$(detect_os)

    # Python
    if ! check_command python3; then
        warn "安装 Python3..."
        case "$os" in
            ubuntu|debian) sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip python3-venv ;;
            centos|rhel|fedora|almalinux|rocky) sudo yum install -y python3 python3-pip ;;
            *) err "请手动安装 Python 3.10+"; exit 1 ;;
        esac
    fi

    # Node.js
    if ! check_command node; then
        warn "安装 Node.js 20..."
        if check_command curl; then
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - 2>/dev/null
            sudo apt-get install -y -qq nodejs 2>/dev/null || sudo yum install -y nodejs 2>/dev/null
        else
            err "请手动安装 Node.js 18+"; exit 1
        fi
    fi

    # Nginx
    if ! check_command nginx; then
        warn "安装 Nginx..."
        case "$os" in
            ubuntu|debian) sudo apt-get install -y -qq nginx ;;
            centos|rhel|fedora|almalinux|rocky) sudo yum install -y nginx ;;
        esac
    fi

    setup_env

    title "安装后端依赖"
    python3 -m venv .venv 2>/dev/null || python3 -m venv .venv --without-pip
    source .venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    info "后端依赖安装完成"

    title "构建前端"
    cd frontend
    npm install --silent 2>/dev/null || npm install
    npm run build
    cd ..
    info "前端构建完成"

    title "配置 Nginx"
    setup_nginx_bare

    title "配置 Systemd 服务"
    setup_systemd

    title "启动服务"
    sudo systemctl daemon-reload
    sudo systemctl enable --now quant-backend
    sudo systemctl reload nginx

    echo ""
    info "部署完成!"
    show_endpoints
}

setup_nginx_bare() {
    local FRONTEND_DIST="$SCRIPT_DIR/frontend/dist"
    local CONF="/etc/nginx/sites-available/ai-quant"
    local ENABLED="/etc/nginx/sites-enabled/ai-quant"

    # 如果没有 sites-available 目录 (CentOS)
    if [[ ! -d /etc/nginx/sites-available ]]; then
        sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
        if ! grep -q "sites-enabled" /etc/nginx/nginx.conf 2>/dev/null; then
            sudo sed -i '/http {/a\    include /etc/nginx/sites-enabled/*;' /etc/nginx/nginx.conf
        fi
    fi

    sudo tee "$CONF" > /dev/null <<NGINX_EOF
server {
    listen 80 default_server;
    server_name _;

    root $FRONTEND_DIST;
    index index.html;

    client_max_body_size 10m;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 1000;

    location / {
        try_files \$uri \$uri/ /index.html;
        add_header Cache-Control "no-cache";
    }

    location /assets/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
NGINX_EOF

    # 移除默认配置
    sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
    sudo ln -sf "$CONF" "$ENABLED"
    sudo nginx -t
    info "Nginx 配置完成"
}

setup_systemd() {
    sudo tee /etc/systemd/system/quant-backend.service > /dev/null <<SERVICE_EOF
[Unit]
Description=AI Quant System Backend
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$SCRIPT_DIR/backend
EnvironmentFile=$SCRIPT_DIR/.env
ExecStart=$SCRIPT_DIR/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
StandardOutput=append:$SCRIPT_DIR/logs/backend.log
StandardError=append:$SCRIPT_DIR/logs/backend.log

[Install]
WantedBy=multi-user.target
SERVICE_EOF

    mkdir -p "$SCRIPT_DIR/logs"
    info "Systemd 服务配置完成"
}

# ============ HTTPS (Let's Encrypt) ============
setup_https() {
    title "配置 HTTPS (Let's Encrypt)"

    if ! check_command certbot; then
        warn "安装 certbot..."
        sudo apt-get install -y -qq certbot python3-certbot-nginx 2>/dev/null || \
        sudo yum install -y certbot python3-certbot-nginx 2>/dev/null
    fi

    read -rp "  输入你的域名 (如 quant.example.com): " domain
    if [[ -z "$domain" ]]; then
        err "域名不能为空"
        return 1
    fi

    read -rp "  输入邮箱 (用于证书通知): " email

    # 更新 Nginx server_name
    sudo sed -i "s/server_name _;/server_name $domain;/" /etc/nginx/sites-available/ai-quant 2>/dev/null || true
    sudo nginx -t && sudo systemctl reload nginx

    sudo certbot --nginx -d "$domain" --non-interactive --agree-tos ${email:+--email "$email"} --redirect

    info "HTTPS 配置完成! 访问: https://$domain"

    # 更新 CORS
    sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=https://$domain|" .env
    sudo systemctl restart quant-backend 2>/dev/null || true
}

# ============ 工具命令 ============
do_update() {
    title "更新部署"
    git pull origin "$(git branch --show-current)"

    if [[ -f docker-compose.yml ]] && docker compose ps &>/dev/null 2>&1; then
        info "Docker 模式更新..."
        COMPOSE="docker compose"
        $COMPOSE ps &>/dev/null || COMPOSE="docker-compose"
        $COMPOSE build --no-cache
        $COMPOSE up -d
    elif systemctl is-active quant-backend &>/dev/null; then
        info "裸机模式更新..."
        source .venv/bin/activate
        pip install -r requirements.txt -q
        cd frontend && npm install --silent && npm run build && cd ..
        sudo systemctl restart quant-backend
        sudo systemctl reload nginx
    else
        warn "未检测到运行中的服务，请先执行部署"
    fi
    info "更新完成"
}

do_stop() {
    title "停止服务"
    if docker compose ps &>/dev/null 2>&1; then
        docker compose down 2>/dev/null || docker-compose down
    fi
    sudo systemctl stop quant-backend 2>/dev/null || true
    info "服务已停止"
}

do_status() {
    title "服务状态"
    echo "--- Docker ---"
    docker compose ps 2>/dev/null || docker-compose ps 2>/dev/null || echo "(Docker 未运行)"
    echo ""
    echo "--- Systemd ---"
    systemctl is-active quant-backend 2>/dev/null && systemctl status quant-backend --no-pager -l 2>/dev/null || echo "(Systemd 服务未运行)"
    echo ""
    echo "--- 端口 ---"
    ss -tlnp 2>/dev/null | grep -E ':(80|8000|3000) ' || netstat -tlnp 2>/dev/null | grep -E ':(80|8000|3000) ' || true
}

do_logs() {
    if docker compose ps &>/dev/null 2>&1; then
        docker compose logs -f --tail=100
    elif [[ -f logs/backend.log ]]; then
        tail -f logs/backend.log
    else
        journalctl -u quant-backend -f 2>/dev/null || echo "无日志"
    fi
}

show_endpoints() {
    local ip
    ip=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "your-server-ip")

    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║          AI Quant System 部署成功!                    ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  前端:    ${GREEN}http://$ip${NC}"
    echo -e "${CYAN}║${NC}  API:     ${GREEN}http://$ip/api/v1${NC}"
    echo -e "${CYAN}║${NC}  文档:    ${GREEN}http://$ip/docs${NC}"
    echo -e "${CYAN}║${NC}  健康:    ${GREEN}http://$ip/health${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  管理命令:                                           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    ./deploy.sh status  — 查看状态                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    ./deploy.sh logs    — 查看日志                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    ./deploy.sh update  — 更新部署                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    ./deploy.sh stop    — 停止服务                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    ./deploy.sh https   — 配置 HTTPS                  ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ============ 主入口 ============
main() {
    echo -e "${CYAN}"
    echo "  ╔═══════════════════════════════════════╗"
    echo "  ║   📈 AI Quant System 一键部署脚本     ║"
    echo "  ╚═══════════════════════════════════════╝"
    echo -e "${NC}"

    local cmd="${1:-}"

    case "$cmd" in
        docker)  deploy_docker ;;
        bare)    deploy_bare ;;
        update)  do_update ;;
        stop)    do_stop ;;
        status)  do_status ;;
        logs)    do_logs ;;
        https)   setup_https ;;
        *)
            echo "  请选择部署模式:"
            echo ""
            echo "    1) Docker 部署  (推荐，需要 Docker)"
            echo "    2) 裸机部署     (直接安装到系统)"
            echo "    3) 查看状态"
            echo "    4) 配置 HTTPS"
            echo "    5) 退出"
            echo ""
            read -rp "  请选择 [1-5]: " choice
            case "$choice" in
                1) deploy_docker ;;
                2) deploy_bare ;;
                3) do_status ;;
                4) setup_https ;;
                5) exit 0 ;;
                *) err "无效选择"; exit 1 ;;
            esac
            ;;
    esac
}

main "$@"
