# 前端项目 CI/CD 配置指南

## ✅ 已配置的内容

已为项目创建了自动化 CI/CD 工作流，支持以下功能：

- **自动构建**：每次 push 到 main/develop 分支时自动构建
- **代码检查**：运行 ESLint 进行代码质量检查
- **自动部署**：构建成功后自动部署到 GitHub Pages

## 📋 必需配置步骤

### 1. 启用 GitHub Pages

1. 进入你的 GitHub 仓库
2. 点击 **Settings** → **Pages**
3. 在 "Build and deployment" 中：
   - Source 选择：**Deploy from a branch**
   - Branch 选择：**gh-pages**
   - Folder 选择：**/ (root)**
4. 点击 **Save**

### 2. 配置 Vite Base 路径（如果需要）

如果你的项目部署到 `https://username.github.io/teaching_assistant/`（而不是根域名），需要修改 `frontend/vite.config.js`：

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/teaching_assistant/',  // 仓库名称
  plugins: [react()],
})
```

如果部署到 `https://username.github.io/` 则保留默认的 `/`

### 3. 确保有 npm-lock 文件

工作流使用 `npm ci` 需要 `package-lock.json`。如果没有，运行：
```bash
cd frontend
npm install
```

## 🚀 使用说明

### 自动部署流程

1. **提交代码**到 main 分支
2. **GitHub Actions 自动触发**：
   - ✅ 安装依赖
   - ✅ 运行 ESLint 检查
   - ✅ 构建项目
   - ✅ 部署到 GitHub Pages
3. **查看部署状态**：
   - 在仓库的 "Actions" 标签页查看工作流执行情况
   - 部署完成后访问你的 GitHub Pages URL

### Pull Request 验证

PR 提交时会自动运行构建和检查，但不会部署。合并到 main 后才会触发部署。

## 📊 工作流触发条件

- **on push to main**: 完整 CI/CD 流程，包括部署
- **on push to develop**: 仅构建和检查，不部署
- **on pull requests**: 仅构建和检查，不部署

## 🔧 后续自定义

可根据需要修改 `.github/workflows/deploy-frontend.yml`：

| 配置项 | 说明 |
|--------|------|
| `node-version` | Node.js 版本，当前为 20 |
| `cache-dependency-path` | package.json 的路径 |
| `retention-days` | 构建产物保留时间 |

## ❓ 常见问题

**Q: 部署后 CSS/JS 资源 404？**
A: 检查 Vite 的 `base` 配置是否与 GitHub Pages URL 匹配

**Q: 工作流失败？**
A: 点击 Actions 标签页查看具体错误日志

**Q: 想禁用 ESLint 检查？**
A: 注释掉工作流中的 "Run linter" 步骤
