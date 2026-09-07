# Phase 1.5 历史矩阵方法定型报告

工程执行：PASSED；开发候选门槛：NOT_SUPPORTED。
历史输入 25，源有效 21，原无效 4。
所有数值从A/B/C raw manifest自动聚合。以下误差为无量纲相对误差，0.005代表0.5%。
随机候选按每checkpoint最差sketch判门槛。迭代数据不是独立统计样本。

## 完整终态

```json
{
  "maximum_identity_error": 1.2163978242526464e-10,
  "initial_GN_failures": 0,
  "adaptive_valid_source_records": 714,
  "adaptive_indicator_triggered": 169,
  "adaptive_not_triggered": 545,
  "adaptive_false_early_0p1percent": 45,
  "raw_status_counts": {
    "A": {
      "PASS": 21,
      "CHECKPOINT_INVALID": 4
    },
    "B": {
      "SOLVER_FAILURE": 960,
      "PASS": 468,
      "CHECKPOINT_INVALID": 272
    },
    "C": {
      "PASS": 3570,
      "CHECKPOINT_INVALID": 680
    }
  }
}
```

## 谱与误差抵消

|问题|seed|状态|条件数|偏离1>0.1|偏离1>0.5|90%能量方向数|chi|
|---|---:|---|---:|---:|---:|---:|---:|
|Allen-Cahn|75|PASS|1.8516|6|0|10|0.72911|
|Allen-Cahn|76|PASS|1.9678|5|1|6|0.58614|
|Allen-Cahn|77|PASS|2.2802|8|1|7|0.9595|
|Allen-Cahn|78|PASS|1.7761|5|0|13|0.74123|
|Allen-Cahn|79|PASS|1.766|4|0|8|0.88043|
|Allen-Cahn|80|PASS|1.7775|6|1|6|0.75527|
|Allen-Cahn|81|CHECKPOINT_INVALID|—|—|—|—|—|
|Allen-Cahn|82|PASS|3.5133|8|2|6|0.59972|
|Allen-Cahn|83|PASS|2.3107|6|0|6|0.63358|
|Allen-Cahn|84|PASS|5.3503|8|2|3|1|
|Burgers|55|PASS|2.9889|8|1|19|0.22294|
|Burgers|56|PASS|3.3729|11|2|13|0.45024|
|Burgers|57|CHECKPOINT_INVALID|—|—|—|—|—|
|Burgers|58|PASS|2.0848|9|0|17|0.05766|
|Burgers|59|PASS|5.0518|18|5|15|0.14879|
|Burgers|60|PASS|1.7974|8|1|27|0.30982|
|Burgers|61|CHECKPOINT_INVALID|—|—|—|—|—|
|Burgers|62|PASS|2.2188|9|1|18|0.19637|
|Burgers|63|CHECKPOINT_INVALID|—|—|—|—|—|
|Burgers|64|PASS|3.1131|15|3|19|0.55241|
|Burgers|65|PASS|2.2765|11|1|19|0.37212|
|Burgers|66|PASS|1.916|10|0|14|0.3633|
|Burgers|67|PASS|4.0837|14|3|9|0.1575|
|Burgers|68|PASS|1.62|7|0|17|0.61069|
|Burgers|69|PASS|2.8176|13|1|14|0.23016|

## 全部候选与预算

|候选|rank|输出|成功checkpoint|中位误差|最差误差|非劣数|中位cold秒|额外setup Gv|进阶|
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
|diagonal|0|fixed_0|21/21|0.012943|0.082067|19|0.0036684|0|False|
|diagonal|0|fixed_1|21/21|0.012833|0.081149|19|0.0037258|0|False|
|diagonal|0|fixed_3|21/21|0.011978|0.08007|19|0.0038515|0|False|
|diagonal|0|fixed_5|21/21|0.010988|0.078442|19|0.0039707|0|False|
|diagonal|0|fixed_10|21/21|0.0087251|0.076925|19|0.004411|0|False|
|diagonal|0|adaptive|21/21|0.011481|0.078442|19|0.0038458|0|False|
|nystrom|4|fixed_0|21/21|0.012943|0.082067|19|0.004968|4|False|
|nystrom|4|fixed_1|21/21|0.012894|0.08175|19|0.0050521|4|False|
|nystrom|4|fixed_3|21/21|0.012806|0.081121|19|0.0052101|4|False|
|nystrom|4|fixed_5|21/21|0.011705|0.07911|19|0.0053984|4|False|
|nystrom|4|adaptive|21/21|0.011705|0.07911|19|0.0053984|4|False|
|nystrom|8|fixed_0|21/21|0.012943|0.082067|19|0.0051213|8|False|
|nystrom|8|fixed_1|21/21|0.012848|0.081811|19|0.0052097|8|False|
|nystrom|8|fixed_3|21/21|0.011502|0.079463|19|0.0053662|8|False|
|nystrom|8|fixed_5|21/21|0.0096419|0.078687|19|0.0055202|8|False|
|nystrom|8|adaptive|21/21|0.0096419|0.078687|19|0.0055202|8|False|
|nystrom|16|fixed_0|21/21|0.012943|0.082067|19|0.0053268|16|False|
|nystrom|16|fixed_1|21/21|0.010325|0.080982|19|0.0054161|16|False|
|nystrom|16|fixed_3|21/21|0.0095972|0.077021|19|0.0055242|16|False|
|nystrom|16|fixed_5|21/21|0.0091491|0.07473|19|0.005601|16|False|
|nystrom|16|adaptive|21/21|0.0091491|0.07473|19|0.005601|16|False|
|nystrom|24|fixed_0|21/21|0.012943|0.082067|19|0.0055019|24|False|
|nystrom|24|fixed_1|21/21|0.010135|0.079694|19|0.0055899|24|False|
|nystrom|24|fixed_3|21/21|0.0092624|0.07505|19|0.0057342|24|False|
|nystrom|24|fixed_5|21/21|0.0070069|0.065146|19|0.0058101|24|False|
|nystrom|24|adaptive|21/21|0.0070069|0.065146|19|0.0057316|24|False|
|nystrom|32|fixed_0|21/21|0.012943|0.082067|19|0.0055863|32|False|
|nystrom|32|fixed_1|21/21|0.0097219|0.078312|19|0.0056716|32|False|
|nystrom|32|fixed_3|21/21|0.0060367|0.059076|19|0.0058204|32|False|
|nystrom|32|fixed_5|21/21|0.003916|0.04444|19|0.005965|32|False|
|nystrom|32|adaptive|21/21|0.003916|0.04444|19|0.0058609|32|False|
|recycled_ritz|4|fixed_0|21/21|0.012943|0.082067|19|0.0036585|0|False|
|recycled_ritz|4|fixed_1|21/21|0.012849|0.081423|19|0.0037061|0|False|
|recycled_ritz|4|fixed_3|21/21|0.01263|0.079298|19|0.0037866|0|False|
|recycled_ritz|4|fixed_5|21/21|0.011642|0.078483|19|0.0038641|0|False|
|recycled_ritz|4|adaptive|21/21|0.011642|0.078483|19|0.0038641|0|False|
|recycled_ritz|8|fixed_0|21/21|0.012943|0.082067|19|0.0043163|0|False|
|recycled_ritz|8|fixed_1|21/21|0.012496|0.080607|19|0.0043659|0|False|
|recycled_ritz|8|fixed_3|21/21|0.011287|0.078903|19|0.0044496|0|False|
|recycled_ritz|8|fixed_5|21/21|0.0092697|0.078157|19|0.0045281|0|False|
|recycled_ritz|8|adaptive|21/21|0.0092697|0.078157|19|0.0045281|0|False|
|recycled_ritz|16|fixed_0|21/21|0.012943|0.082067|19|0.0044084|0|False|
|recycled_ritz|16|fixed_1|21/21|0.0096136|0.079319|19|0.0044993|0|False|
|recycled_ritz|16|fixed_3|21/21|0.0090478|0.074433|19|0.0046704|0|False|
|recycled_ritz|16|fixed_5|21/21|0.0084848|0.072574|19|0.0048233|0|False|
|recycled_ritz|16|adaptive|21/21|0.0084848|0.072574|19|0.0048233|0|False|
|recycled_ritz|24|fixed_0|21/21|0.012943|0.082067|19|0.0046449|0|False|
|recycled_ritz|24|fixed_1|21/21|0.0097212|0.075903|19|0.0047277|0|False|
|recycled_ritz|24|fixed_3|21/21|0.0079238|0.069768|19|0.0048885|0|False|
|recycled_ritz|24|fixed_5|21/21|0.0057142|0.056113|19|0.0049902|0|False|
|recycled_ritz|24|adaptive|21/21|0.0057142|0.056113|19|0.0049902|0|False|
|hybrid_defect|8|fixed_0|21/21|0.012943|0.082067|19|0.0043412|1|False|
|hybrid_defect|8|fixed_1|21/21|0.01243|0.081129|19|0.0044248|1|False|
|hybrid_defect|8|fixed_3|21/21|0.012001|0.080415|19|0.0045798|1|False|
|hybrid_defect|8|fixed_5|21/21|0.01185|0.080371|19|0.0046602|1|False|
|hybrid_defect|8|adaptive|21/21|0.01185|0.082067|19|0.0043412|1|False|
|hybrid_defect|16|fixed_0|21/21|0.012943|0.082067|19|0.0043465|1|False|
|hybrid_defect|16|fixed_1|21/21|0.0090628|0.078043|19|0.0044258|1|False|
|hybrid_defect|16|fixed_3|21/21|0.0087525|0.074922|19|0.0045631|1|False|
|hybrid_defect|16|fixed_5|21/21|0.0083802|0.074288|19|0.0046988|1|False|
|hybrid_defect|16|adaptive|21/21|0.0083802|0.074288|19|0.0046988|1|False|
|hybrid_defect|24|fixed_0|21/21|0.012943|0.082067|19|0.0042386|1|False|
|hybrid_defect|24|fixed_1|21/21|0.0084873|0.072338|19|0.0043006|1|False|
|hybrid_defect|24|fixed_3|21/21|0.00743|0.06852|19|0.0044035|1|False|
|hybrid_defect|24|fixed_5|21/21|0.0072208|0.063162|19|0.0045064|1|False|
|hybrid_defect|24|adaptive|21/21|0.0072208|0.063162|19|0.0045064|1|False|
|exact_gn|-1|fixed_0|21/21|0.012943|0.082067|19|0.0033088|0|False|
|exact_gn|-1|fixed_1|21/21|0.00085883|0.021841|21|0.003458|0|False|
|exact_gn|-1|fixed_3|21/21|5.585e-07|0.00058631|21|0.0038217|0|False|
|exact_gn|-1|adaptive|21/21|0.00014545|0.0011016|21|0.0036631|0|False|

## 选择

```json
{
  "fixed": null,
  "adaptive": null
}
```
若没有合格候选，按协议停止，不增加rank、预算或替换检查点。若有合格候选，也仅说明历史开发可行，未授权进入训练。

## Zero-start 与 GN-start

|候选|rank|目标误差|双侧达到/计划配对|GN步数更少|GN cold更快|zero中位步数|GN中位步数|
|---|---:|---:|---:|---:|---:|---:|---:|
|diagonal|0|0.05|4/25|4|0|29.0|0.0|
|diagonal|0|0.01|0/25|0|0|None|None|
|diagonal|0|0.001|0/25|0|0|None|None|
|diagonal|0|0.0001|0/25|0|0|None|None|
|nystrom|4|0.05|5/125|5|2|31.0|0.0|
|nystrom|4|0.01|0/125|0|0|None|None|
|nystrom|4|0.001|0/125|0|0|None|None|
|nystrom|4|0.0001|0/125|0|0|None|None|
|nystrom|8|0.05|40/125|40|8|24.0|0.0|
|nystrom|8|0.01|38/125|38|12|25.0|0.0|
|nystrom|8|0.001|29/125|29|7|25.0|13.0|
|nystrom|8|0.0001|20/125|20|2|27.0|20.0|
|nystrom|16|0.05|101/125|101|5|35.0|0.0|
|nystrom|16|0.01|95/125|94|7|37.0|1.0|
|nystrom|16|0.001|84/125|81|0|15.5|15.0|
|nystrom|16|0.0001|67/125|62|1|16.0|12.0|
|nystrom|24|0.05|105/125|105|0|18.0|0.0|
|nystrom|24|0.01|105/125|105|0|20.0|1.0|
|nystrom|24|0.001|105/125|102|0|23.0|15.0|
|nystrom|24|0.0001|105/125|105|0|28.0|21.0|
|nystrom|32|0.05|105/125|105|0|9.0|0.0|
|nystrom|32|0.01|105/125|105|0|9.0|1.0|
|nystrom|32|0.001|105/125|105|0|13.0|7.0|
|nystrom|32|0.0001|105/125|105|0|14.0|9.0|
|recycled_ritz|4|0.05|2/25|2|2|32.0|0.0|
|recycled_ritz|4|0.01|0/25|0|0|None|None|
|recycled_ritz|4|0.001|0/25|0|0|None|None|
|recycled_ritz|4|0.0001|0/25|0|0|None|None|
|recycled_ritz|8|0.05|8/25|8|8|23.0|0.0|
|recycled_ritz|8|0.01|8/25|8|8|23.5|0.0|
|recycled_ritz|8|0.001|6/25|6|5|24.5|13.5|
|recycled_ritz|8|0.0001|4/25|4|4|27.0|18.5|
|recycled_ritz|16|0.05|21/25|21|19|31.0|0.0|
|recycled_ritz|16|0.01|20/25|20|19|35.5|1.0|
|recycled_ritz|16|0.001|17/25|16|14|15.0|15.0|
|recycled_ritz|16|0.0001|15/25|14|11|17.0|11.0|
|recycled_ritz|24|0.05|21/25|21|16|16.0|0.0|
|recycled_ritz|24|0.01|21/25|20|15|19.0|1.0|
|recycled_ritz|24|0.001|21/25|21|12|21.0|14.0|
|recycled_ritz|24|0.0001|21/25|20|11|24.0|20.0|
|hybrid_defect|8|0.05|3/25|3|3|29.0|0.0|
|hybrid_defect|8|0.01|2/25|2|2|32.5|0.0|
|hybrid_defect|8|0.001|0/25|0|0|None|None|
|hybrid_defect|8|0.0001|0/25|0|0|None|None|
|hybrid_defect|16|0.05|14/25|14|12|10.0|0.0|
|hybrid_defect|16|0.01|11/25|11|9|10.0|0.0|
|hybrid_defect|16|0.001|10/25|10|8|16.0|8.0|
|hybrid_defect|16|0.0001|9/25|9|7|16.0|10.0|
|hybrid_defect|24|0.05|21/25|21|12|21.0|0.0|
|hybrid_defect|24|0.01|21/25|20|11|26.0|1.0|
|hybrid_defect|24|0.001|20/25|20|11|30.5|16.5|
|hybrid_defect|24|0.0001|20/25|19|10|34.0|21.0|
|exact_gn|-1|0.05|21/25|21|0|1.0|0.0|
|exact_gn|-1|0.01|21/25|19|0|2.0|1.0|
|exact_gn|-1|0.001|21/25|21|0|2.0|1.0|
|exact_gn|-1|0.0001|21/25|20|0|3.0|2.0|

## 审计与限制

变差的有效输出共 328 条（含预算及sketch重复，不是独立checkpoint数量）；完整逐条数据见summary.json。
B的SOLVER_FAILURE可能是n_theta步内未达到严格响应残差；C在既定预算获得有限、通过核验的输出仍可PASS，但不保证曲率精度。
cold时间包含GN初始化；incremental时间扣除已完成的GN初始化。exact GN和diagonal的稠密访问性质明确保留。
所有Gv/Hv为已归档矩阵乘法。真实JVP/VJP/HVP调用为0；不能外推GPU/matrix-free速度。完整native峰值内存未测。
eta是indicator；存在过早停止时按原阈值保留，不用oracle补算或回退挑结果。
历史文件缺失导致的legacy validator失败单独记录。本阶段不恢复原有删除文件，不声称全仓库通过。
