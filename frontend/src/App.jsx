import { useEffect, useMemo, useState } from "react";
import { calculateFolder, getCalculation, getHealth, scanFolder } from "./api";

const workflowSteps = [
  "1. 数据导入",
  "2. 脚本匹配",
  "3. 规则清洗",
  "4. 正式测算",
  "5. 异常追溯",
  "6. 复盘报告",
];

const metricCards = [
  ["memberRevenue", "会员收入", "会员费直接收入"],
  ["benefitCost", "权益成本", "核销成本 + 服务成本"],
  ["incrementalGmv", "增量 GMV", "会员带来的增量交易额"],
  ["memberProfit", "会员毛利", "收入 + 增量毛利 - 成本"],
  ["roi", "ROI", "会员毛利 / 权益成本"],
  ["ltv", "LTV", "生命周期价值"],
];

const advancedMetricCards = [
  ["memberValueScore", "会员价值分", "综合 ROI、续费、价格敏感度后的评分"],
  ["netSequenceValue", "净序列价值", "扣除权益挤压后的长期净贡献"],
  ["priceSensitivityIndex", "价格敏感度", "定价相对目标用户 ARPU 的压力"],
  ["benefitCrowdingLoss", "权益挤压损失", "高核销权益对净贡献的侵蚀"],
  ["renewalQualityScore", "续费质量分", "续费率与生命周期的合成指标"],
  ["formulaConfidenceScore", "模型置信度", "基于样本完整度与规则稳定性的估计"],
];

const riskLabels = {
  low: "低风险",
  medium: "中风险",
  high: "高风险",
};

function formatNumber(value) {
  if (typeof value !== "number") return value;
  return value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

function formatMetric(key, value) {
  if (key === "roi") return `${Number(value).toFixed(2)}x`;
  if (key === "breakEvenRenewalRate" || key === "benefitUsageRate") {
    return `${Math.round(Number(value) * 100)}%`;
  }
  return formatNumber(value);
}

function riskClass(level) {
  if (level === "high") return "risk high";
  if (level === "medium") return "risk medium";
  return "risk low";
}

function buildPlanAdvice(plan, trace, issues) {
  if (!plan || !trace) return [];
  const advanced = plan.advancedMetrics || {};
  const advice = [
    `${plan.planName} 当前 ROI 为 ${formatMetric("roi", plan.roi)}，会员价值分为 ${formatNumber(advanced.memberValueScore)}，净序列价值为 ${formatNumber(advanced.netSequenceValue)}。`,
  ];

  if (trace.riskLevel === "high") {
    advice.push("主要风险：当前方案经济性偏弱，建议先调整价格或降低高成本权益。");
  } else if (trace.riskLevel === "medium") {
    advice.push("主要风险：方案对权益核销率较敏感，建议设置成本上限并小流量验证。");
  } else {
    advice.push("样例模型下方案较健康，可以优先验证转化率、复购率和真实续费率。");
  }

  if (issues.length > 0) {
    advice.push("校验模块发现当前方案仍有风险提醒，上线前建议完成业务复核。");
  } else {
    advice.push("当前方案没有阻塞性异常，可以进入灰度实验设计。");
  }

  if (advanced.priceSensitivityIndex > 0.18) {
    advice.push("价格敏感度偏高，建议增加分层定价或权益差异化，避免高价方案压低转化。");
  }
  if (advanced.benefitCrowdingLoss > plan.memberProfit * 0.12) {
    advice.push("权益挤压损失较明显，建议设置优惠券核销上限、免邮门槛或权益冷却周期。");
  }

  advice.push("下一步实验：按高价值用户和价格敏感用户分层，对价格、权益数量和免邮门槛做 A/B 测试。");
  return advice;
}

function buildPlanReport(plan, trace) {
  if (!plan || !trace) return null;
  const advanced = plan.advancedMetrics || {};
  return {
    title: `${plan.planName} 会员 ROI 复盘`,
    scenario: `${plan.planName} 会员 ROI 测算`,
    summary: `${plan.planName} 预估会员收入为 ${formatNumber(plan.memberRevenue)}，权益成本为 ${formatNumber(plan.benefitCost)}，会员毛利为 ${formatNumber(plan.memberProfit)}，ROI 为 ${formatMetric("roi", plan.roi)}。高级模型给出的会员价值分为 ${formatNumber(advanced.memberValueScore)}，模型置信度为 ${formatNumber(advanced.formulaConfidenceScore)}。当前风险等级为 ${riskLabels[trace.riskLevel]}。`,
    nextStep: trace.riskLevel === "high"
      ? "建议先回到权益规则和定价层做方案收敛，再进入灰度。"
      : "建议进入小范围灰度，持续对比预测 ROI、真实续费率和权益核销率。",
  };
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [calculation, setCalculation] = useState(null);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [folderPath, setFolderPath] = useState("");
  const [scanResult, setScanResult] = useState(null);
  const [isLocked, setIsLocked] = useState(false);
  const [hasExecuted, setHasExecuted] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadHealth() {
      try {
        setHealth(await getHealth());
      } catch (err) {
        setError(err.message);
      }
    }
    loadHealth();
  }, []);

  async function handleScanFolder() {
    try {
      setIsScanning(true);
      const result = await scanFolder(folderPath.trim());
      setScanResult(result);
      setIsLocked(false);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsScanning(false);
    }
  }

  async function executeCalculation() {
    try {
      const calculationData = folderPath.trim()
        ? await calculateFolder(folderPath.trim())
        : await getCalculation();
      setCalculation(calculationData);
      setSelectedPlanId(
        calculationData?.plans?.find((plan) => plan.planId === "plus_annual")
          ?.planId || calculationData?.plans?.[0]?.planId,
      );
      setHasExecuted(true);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  const selectedPlan = useMemo(() => {
    if (!calculation?.plans?.length) return null;
    return (
      calculation.plans.find((plan) => plan.planId === selectedPlanId) ||
      calculation.plans[0]
    );
  }, [calculation, selectedPlanId]);

  const selectedTrace = useMemo(() => {
    if (!calculation?.trace?.planTraces || !selectedPlan) return null;
    return calculation.trace.planTraces.find(
      (item) => item.planId === selectedPlan.planId,
    );
  }, [calculation, selectedPlan]);

  const selectedIssues = useMemo(() => {
    if (!calculation?.validationIssues || !selectedPlan) return [];
    return calculation.validationIssues.filter(
      (item) => !item.planId || item.planId === selectedPlan.planId,
    );
  }, [calculation, selectedPlan]);

  const selectedAdvice = useMemo(
    () => buildPlanAdvice(selectedPlan, selectedTrace, selectedIssues),
    [selectedPlan, selectedTrace, selectedIssues],
  );

  const selectedReport = useMemo(
    () => buildPlanReport(selectedPlan, selectedTrace),
    [selectedPlan, selectedTrace],
  );

  const scanItems = scanResult?.items || [];

  return (
    <main className="appShell">
      <aside className="sidebar">
        <div className="brand">
          <span>MemberPilot AI</span>
          <strong>会员测算脚本台</strong>
        </div>
        <nav>
          {workflowSteps.map((step, index) => (
            <div
              className={`navItem ${hasExecuted || index < 2 ? "active" : ""}`}
              key={step}
            >
              <span>{index + 1}</span>
              {step}
            </div>
          ))}
        </nav>
        <div className="localNote">
          本地运行：仅连接 127.0.0.1。
          <br />
          文件夹路径只用于本机扫描，不保存路径，不回传真实文件名。
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">从业务自动化测算延展到会员 ROI 测算</p>
            <h1>会员权益 ROI 与定价测算流程工作台</h1>
            <p className="subtitle">
              统一导入数据，自动匹配脚本模块，再由写死公式计算会员收入、权益成本、增量 GMV、ROI、LTV 和风险追溯。
            </p>
          </div>
          <div className="status">
            <span className={health?.status === "ok" ? "dot ok" : "dot"} />
            <span>{health?.status === "ok" ? "后端已连接" : "后端检查中"}</span>
          </div>
        </header>

        {error && (
          <section className="error">
            后端暂未连接：{error}。请确认 FastAPI 正在 8000 端口运行。
          </section>
        )}

        <section className="panel importPanel">
          <div className="sectionTitle">
            <p className="label">Step 01</p>
            <h2>批量路径配置</h2>
            <p>
              填入一个本地数据文件夹路径，系统自动检索 CSV，并按字段优先、文件名辅助匹配到会员方案、用户分层、订单和权益核销脚本。
            </p>
          </div>
          <div className="pathBox">
            <label>
              数据文件夹路径
              <input
                placeholder="示例数据可输入 ../samples；留空则使用 samples 样例数据"
                type="text"
                value={folderPath}
                onChange={(event) => {
                  setFolderPath(event.target.value);
                  setScanResult(null);
                  setIsLocked(false);
                }}
              />
            </label>
            <button type="button" onClick={handleScanFolder} disabled={isScanning}>
              {isScanning ? "扫描中" : "按文件夹自动匹配 M01/M02/M03 文件"}
            </button>
          </div>
          <p className="pathHint">示例数据可输入 <code>../samples</code>。系统只在本机扫描，不保存真实路径。</p>
          <div className="matchStats">
            <div>
              <span>当前已匹配</span>
              <strong>{scanResult?.matchedCount ?? 0}</strong>
            </div>
            <div>
              <span>当前未匹配</span>
              <strong>{scanResult?.unmatchedCount ?? 0}</strong>
            </div>
          </div>
          <details className="matchDetails">
            <summary>查看自动匹配明细</summary>
            <div className="matchGrid">
              {(scanItems.length ? scanItems : [
                { sourceId: "empty_1", dataset: "会员方案数据", rowCount: 0, status: "待扫描" },
                { sourceId: "empty_2", dataset: "用户分层数据", rowCount: 0, status: "待扫描" },
                { sourceId: "empty_3", dataset: "订单数据", rowCount: 0, status: "待扫描" },
                { sourceId: "empty_4", dataset: "权益核销数据", rowCount: 0, status: "待扫描" },
              ]).map((item) => (
                <div className="matchItem" key={item.sourceId}>
                  <span>{item.dataset}</span>
                  <strong>{item.status} / {item.rowCount} 行</strong>
                </div>
              ))}
            </div>
          </details>

          <div className="lockArea">
            <div>
              <h3>自动锁定结果确认区</h3>
              <p>没匹配到的数据类型会自动用样例数据补齐；无法识别的数据会空置或忽略，不影响核心脚本继续执行。</p>
            </div>
            <button type="button" onClick={() => setIsLocked(true)}>
              页面锁定
            </button>
          </div>
          {scanItems.length > 0 && (
            <div className="lockedList">
              {scanItems.slice(0, 6).map((item) => (
                <div key={`locked-${item.sourceId}`}>
                  <span>{item.dataset}</span>
                  <strong>{item.status} / {item.rowCount} 行</strong>
                </div>
              ))}
            </div>
          )}
          <div className={isLocked ? "notice success" : "notice"}>
            {isLocked
              ? "匹配结果已锁定。正式执行时会按当前文件夹扫描结果进入后端脚本计算。"
              : "你可以先扫描并锁定文件夹数据，也可以留空直接使用 samples 样例数据运行。"}
          </div>
          <div className="scriptRelation">
            <div>
              <span>M01 / data_loader.py</span>
              <strong>读取文件夹 CSV，按字段结构识别业务数据类型</strong>
            </div>
            <div>
              <span>M02 / rule_engine.py</span>
              <strong>清洗会员价格、权益规则、续费率和核销限制</strong>
            </div>
            <div>
              <span>M03 / calculator.py</span>
              <strong>调用写死公式计算 ROI、LTV、会员毛利和盈亏平衡点</strong>
            </div>
          </div>
        </section>

        <section className="panel scriptPanel">
          <div className="sectionTitle">
            <p className="label">Step 02</p>
            <h2>自动匹配脚本代码</h2>
            <p>
              后端按模块脚本执行：数据导入、规则解析、测算公式、异常校验、追溯解释、AI 建议。
            </p>
          </div>
          <div className="scriptGrid">
            {(calculation?.pipeline?.scriptMatches || [
              {
                id: "M01",
                name: "数据导入与完整性检查",
                module: "data_loader.py",
                status: "待执行",
                description: "读取会员方案、用户分层、订单和权益核销数据。",
              },
              {
                id: "M02",
                name: "会员规则清洗计算层",
                module: "rule_engine.py",
                status: "待执行",
                description: "解析会员价格、权益包和续费假设。",
              },
              {
                id: "M03",
                name: "增量价值与权益成本测算",
                module: "calculator.py",
                status: "待执行",
                description: "用写死公式计算会员方案是否赚钱。",
              },
            ]).map((script) => (
              <article className="scriptCard" key={script.id}>
                <div>
                  <span>{script.id}</span>
                  <strong>{script.name}</strong>
                </div>
                <p>{script.description}</p>
                <footer>
                  <code>{script.module}</code>
                  <em>{script.status}</em>
                </footer>
              </article>
            ))}
          </div>
          <button className="primaryAction" type="button" onClick={executeCalculation}>
            正式执行会员测算
          </button>
        </section>

        {calculation && selectedPlan && (
          <>
            <section className="panel executionPanel">
              <div className="sectionTitle">
                <p className="label">Step 03</p>
                <h2>脚本执行结果</h2>
                <p>{calculation.pipeline.dataSourceNote}</p>
              </div>
              {calculation.uploadSummary.length > 0 && (
                <div className="uploadSummary">
                  {calculation.uploadSummary.map((item) => (
                    <div key={item.sourceId}>
                      <span>{item.dataset}</span>
                      <strong>{item.status} / {item.rowCount} 行</strong>
                    </div>
                  ))}
                </div>
              )}
              <div className="timeline">
                {calculation.pipeline.steps.map((step) => (
                  <article key={step.id}>
                    <span>{step.id}</span>
                    <div>
                      <strong>{step.title}</strong>
                      <p>{step.summary}</p>
                      <ul>
                        {step.logs.map((log) => (
                          <li key={log}>{log}</li>
                        ))}
                      </ul>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="panel selector">
              <div>
                <p className="label">Step 04</p>
                <h2>会员方案选择</h2>
              </div>
              <select
                value={selectedPlan.planId}
                onChange={(event) => setSelectedPlanId(event.target.value)}
              >
                {calculation.plans.map((plan) => (
                  <option value={plan.planId} key={plan.planId}>
                    {plan.planName}
                  </option>
                ))}
              </select>
              <div className="planMeta">
                <span>{selectedPlan.periodMonths} 个月</span>
                <span>{formatNumber(selectedPlan.targetMembers)} 名目标会员</span>
                <span>价格 {formatNumber(selectedPlan.price)}</span>
                <span className={riskClass(selectedTrace?.riskLevel)}>
                  {riskLabels[selectedTrace?.riskLevel] || "低风险"}
                </span>
              </div>
            </section>

            <section className="metrics">
              {metricCards.map(([key, title, desc]) => (
                <article className="metric" key={key}>
                  <span>{title}</span>
                  <strong>{formatMetric(key, selectedPlan[key])}</strong>
                  <small>{desc}</small>
                </article>
              ))}
            </section>

            <section className="panel advancedModel">
              <div className="sectionTitle">
                <p className="label">高级模型</p>
                <h2>会员价值重估模型</h2>
                <p>
                  在基础 ROI 之外，引入价格敏感度、权益挤压损失、续费质量和模型置信度，用于判断会员方案是否具备长期商业价值。
                </p>
              </div>
              <div className="advancedGrid">
                {advancedMetricCards.map(([key, title, desc]) => (
                  <article className="advancedMetric" key={key}>
                    <span>{title}</span>
                    <strong>{formatMetric(key, selectedPlan.advancedMetrics?.[key])}</strong>
                    <small>{desc}</small>
                  </article>
                ))}
              </div>
              <div className="formulaGrid">
                {calculation.advancedFormulaCards.map((item) => (
                  <article key={item.title}>
                    <h3>{item.title}</h3>
                    <code>{item.formula}</code>
                    <p>{item.meaning}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="panel productStrategy">
              <div className="sectionTitle">
                <p className="label">产品决策</p>
                <h2>上线判断与实验设计</h2>
                <p>
                  把计算结果转成产品经理可执行的决策：是否上线、先验证哪个人群、做什么实验、看哪些护栏指标。
                </p>
              </div>
              <div className="decisionHero">
                <div>
                  <span>推荐动作</span>
                  <strong>{calculation.productStrategy.decisionSummary.recommendation}</strong>
                  <p>{calculation.productStrategy.decisionSummary.reason}</p>
                </div>
                <div>
                  <span>优先方案</span>
                  <strong>{calculation.productStrategy.decisionSummary.priorityPlan}</strong>
                  <p>
                    ROI {formatMetric("roi", calculation.productStrategy.decisionSummary.expectedROI)}
                    ，会员价值分 {formatNumber(calculation.productStrategy.decisionSummary.memberValueScore)}
                  </p>
                </div>
              </div>
              <div className="strategyGrid">
                <article>
                  <h3>方案决策列表</h3>
                  <div className="compactList">
                    {calculation.productStrategy.planDecisions.slice(0, 5).map((item) => (
                      <div key={item.planId}>
                        <span>{item.planName}</span>
                        <strong>{item.action} / 价值分 {formatNumber(item.memberValueScore)}</strong>
                      </div>
                    ))}
                  </div>
                </article>
                <article>
                  <h3>用户分层机会</h3>
                  <div className="compactList">
                    {calculation.productStrategy.segmentOpportunities.map((item) => (
                      <div key={item.segmentName}>
                        <span>{item.segmentName}</span>
                        <strong>{item.suggestedTactic}</strong>
                      </div>
                    ))}
                  </div>
                </article>
              </div>
              <div className="experimentGrid">
                {calculation.productStrategy.experimentPlan.map((item) => (
                  <article key={item.name}>
                    <h3>{item.name}</h3>
                    <p>{item.hypothesis}</p>
                    <div><span>A</span>{item.variantA}</div>
                    <div><span>B</span>{item.variantB}</div>
                    <strong>主指标：{item.primaryMetric}</strong>
                    <small>护栏：{item.guardrail}</small>
                  </article>
                ))}
              </div>
              <div className="guardrailGrid">
                {calculation.productStrategy.metricGuardrails.map((item) => (
                  <div key={item.metric}>
                    <span>{item.metric}</span>
                    <strong>{formatNumber(item.current)}</strong>
                    <small>{item.target}</small>
                  </div>
                ))}
              </div>
            </section>

            <section className="grid">
              <article className="panel">
                <p className="label">Step 05</p>
                <h2>测算公式拆解</h2>
                <div className="detailList">
                  <div>
                    <span>会员收入</span>
                    <strong>价格 * 目标会员数 = {formatNumber(selectedPlan.memberRevenue)}</strong>
                  </div>
                  <div>
                    <span>权益成本</span>
                    <strong>核销成本 + 服务成本 = {formatNumber(selectedPlan.benefitCost)}</strong>
                  </div>
                  <div>
                    <span>会员毛利</span>
                    <strong>收入 + 增量毛利 - 成本 = {formatNumber(selectedPlan.memberProfit)}</strong>
                  </div>
                  <div>
                    <span>盈亏平衡续费率</span>
                    <strong>{formatMetric("breakEvenRenewalRate", selectedPlan.breakEvenRenewalRate)}</strong>
                  </div>
                </div>
              </article>

              <article className="panel">
                <p className="label">异常校验</p>
                <h2>正确率控制结果</h2>
                {selectedIssues.length ? (
                  <ul className="issueList">
                    {selectedIssues.map((issue) => (
                      <li key={`${issue.planId || issue.scope}-${issue.message}`}>
                        {issue.message}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="empty">当前方案没有阻塞性异常，建议继续观察权益成本和续费率。</p>
                )}
              </article>

              <article className="panel">
                <p className="label">AI 追溯</p>
                <h2>ROI 偏差来源</h2>
                <ul>
                  {selectedTrace?.drivers?.map((driver) => (
                    <li key={driver}>{driver}</li>
                  ))}
                </ul>
              </article>

              <article className="panel">
                <p className="label">AI 建议</p>
                <h2>下一步实验建议</h2>
                <ul>
                  {selectedAdvice.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
            </section>

            <section className="panel tablePanel">
              <p className="label">方案对比</p>
              <h2>会员方案对比表</h2>
              <div className="tableWrap">
                <table>
                  <thead>
                    <tr>
                      <th>方案</th>
                      <th>价格</th>
                      <th>目标会员</th>
                      <th>会员收入</th>
                      <th>权益成本</th>
                      <th>会员毛利</th>
                      <th>ROI</th>
                      <th>LTV</th>
                      <th>核销率</th>
                    </tr>
                  </thead>
                  <tbody>
                    {calculation.plans.map((plan) => (
                      <tr
                        className={plan.planId === selectedPlan.planId ? "selectedRow" : ""}
                        key={plan.planId}
                      >
                        <td>{plan.planName}</td>
                        <td>{formatNumber(plan.price)}</td>
                        <td>{formatNumber(plan.targetMembers)}</td>
                        <td>{formatNumber(plan.memberRevenue)}</td>
                        <td>{formatNumber(plan.benefitCost)}</td>
                        <td>{formatNumber(plan.memberProfit)}</td>
                        <td>{formatMetric("roi", plan.roi)}</td>
                        <td>{formatNumber(plan.ltv)}</td>
                        <td>{formatMetric("benefitUsageRate", plan.benefitUsageRate)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="panel report">
              <p className="label">Step 06</p>
              <h2>{selectedReport?.title}</h2>
              <p>{selectedReport?.summary}</p>
              <div className="reportGrid">
                <div>
                  <span>当前场景</span>
                  <strong>{selectedReport?.scenario}</strong>
                </div>
                <div>
                  <span>复盘结论</span>
                  <strong>{selectedReport?.nextStep}</strong>
                </div>
              </div>
            </section>
          </>
        )}
      </section>
    </main>
  );
}
