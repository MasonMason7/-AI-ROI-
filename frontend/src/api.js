const API_BASE = "http://127.0.0.1:8000";
const DEMO_DATA_URL = `${import.meta.env.BASE_URL}demo-calculation.json`;

function isStaticDemo() {
  return (
    import.meta.env.VITE_STATIC_DEMO === "true" ||
    window.location.hostname.endsWith("github.io") ||
    window.location.protocol === "file:"
  );
}

async function getDemoCalculation() {
  const response = await fetch(DEMO_DATA_URL);
  if (!response.ok) throw new Error("静态 Demo 数据读取失败");
  return response.json();
}

export async function getHealth() {
  if (isStaticDemo()) {
    return { status: "ok", service: "MemberPilot AI 静态 Demo" };
  }

  const response = await fetch(`${API_BASE}/api/health`);
  if (!response.ok) throw new Error("健康检查失败");
  return response.json();
}

export async function getCalculation(files = []) {
  if (isStaticDemo()) {
    return getDemoCalculation();
  }

  if (files.length > 0) {
    const uploadedFiles = await Promise.all(
      files.map(async (file) => ({
        filename: file.name,
        content: await file.text(),
      })),
    );
    const response = await fetch(`${API_BASE}/api/calculate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ files: uploadedFiles }),
    });
    if (!response.ok) throw new Error("上传测算请求失败");
    return response.json();
  }

  try {
    const response = await fetch(`${API_BASE}/api/calculate`);
    if (!response.ok) throw new Error("测算请求失败");
    return response.json();
  } catch (error) {
    return getDemoCalculation();
  }
}

export async function scanFolder(folderPath) {
  if (isStaticDemo()) {
    return {
      status: "ok",
      message: "静态 Demo 已使用内置样例数据完成匹配。",
      matchedCount: 4,
      unmatchedCount: 0,
      items: [
        { sourceId: "demo_1", dataset: "会员方案数据", rowCount: 10, status: "已匹配" },
        { sourceId: "demo_2", dataset: "用户分层数据", rowCount: 10, status: "已匹配" },
        { sourceId: "demo_3", dataset: "订单数据", rowCount: 20, status: "已匹配" },
        { sourceId: "demo_4", dataset: "权益核销数据", rowCount: 20, status: "已匹配" },
      ],
    };
  }

  const response = await fetch(`${API_BASE}/api/scan-folder`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ folderPath }),
  });
  if (!response.ok) throw new Error("文件夹扫描失败");
  return response.json();
}

export async function calculateFolder(folderPath) {
  if (isStaticDemo()) {
    return getDemoCalculation();
  }

  const response = await fetch(`${API_BASE}/api/calculate-folder`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ folderPath }),
  });
  if (!response.ok) throw new Error("文件夹测算失败");
  return response.json();
}
