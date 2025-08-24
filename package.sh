#!/bin/bash
# 疏散中心选址系统 - 主打包脚本

echo "🎁 疏散中心选址决策支持系统打包工具"
echo "========================================="
echo ""
echo "请选择打包方式："
echo "1. 快速打包 (仅项目文件 + Docker配置)"
echo "2. 完整打包 (包含现有Docker容器和数据)"
echo "3. 仅导出Docker容器和数据"
echo "4. Python脚本打包 (最完整)"
echo ""

read -p "请输入选择 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚀 执行快速打包..."
        chmod +x quick_package.sh
        ./quick_package.sh
        ;;
    2)
        echo ""
        echo "🔄 先导出Docker数据..."
        chmod +x export_docker.sh
        ./export_docker.sh
        
        echo ""
        echo "📦 然后执行项目打包..."
        chmod +x quick_package.sh
        ./quick_package.sh
        
        # 将Docker导出合并到项目包中
        DOCKER_EXPORT=$(ls -t docker_export_* 2>/dev/null | head -1)
        PROJECT_PACKAGE=$(ls -t package/evacuation_center_system_* 2>/dev/null | head -1)
        
        if [ -d "$DOCKER_EXPORT" ] && [ -d "$PROJECT_PACKAGE" ]; then
            echo ""
            echo "🔗 合并Docker数据到项目包..."
            cp -r "$DOCKER_EXPORT"/* "$PROJECT_PACKAGE/"
            
            # 重新打包
            cd package
            PACKAGE_NAME=$(basename "$PROJECT_PACKAGE")
            rm -f "${PACKAGE_NAME}.zip" 2>/dev/null
            zip -r "${PACKAGE_NAME}_complete.zip" "$PACKAGE_NAME" > /dev/null 2>&1
            
            COMPLETE_SIZE=$(du -sh "${PACKAGE_NAME}_complete.zip" | cut -f1)
            echo "✅ 完整包创建成功: package/${PACKAGE_NAME}_complete.zip ($COMPLETE_SIZE)"
        fi
        ;;
    3)
        echo ""
        echo "🐳 仅导出Docker容器和数据..."
        chmod +x export_docker.sh
        ./export_docker.sh
        ;;
    4)
        echo ""
        echo "🐍 执行Python完整打包..."
        python3 package_project.py
        ;;
    *)
        echo "❌ 无效选择，退出"
        exit 1
        ;;
esac

echo ""
echo "🎉 操作完成！"
