"""
manuscript_content.py -- single source of truth for the manuscript, consumed by both
the .docx renderer (08) and the reportlab .pdf renderer (11). Returns an ordered list
of typed blocks. The neural-baseline subsection/table are populated dynamically from
results/<ds>_neural_summary.json so the numbers always match the analysis.
"""
import os, json
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')

TITLE = ('Evaluation design decides the winner: horizon, leakage and metric effects '
         'in intermittent demand forecasting')
AUTHORS = ['Nishchay Patel']
AFFIL = 'Independent Researcher'

# Verified DOIs (Crossref-resolved + title/year-checked). (needle in ref string) -> suffix.
# Conference papers without a registered DOI (LightGBM/NeurIPS, EO 14017) get no suffix;
# N-BEATS (ICLR/OpenReview) carries its arXiv identifier instead.
DOIS = [
    ('Bacchetti, A., Saccani, N., 2012.', ' https://doi.org/10.1016/j.omega.2011.06.008'),
    ('Babai, M.Z., Syntetos, A.A., Teunter, R., 2014.', ' https://doi.org/10.1016/j.ijpe.2014.08.019'),
    ('Bojer, C.S., Meldgaard, J.P., 2021.', ' https://doi.org/10.1016/j.ijforecast.2020.07.007'),
    ('Challu, C., Olivares', ' https://doi.org/10.1609/aaai.v37i6.25854'),
    ('Chen, T., Guestrin, C., 2016.', ' https://doi.org/10.1145/2939672.2939785'),
    ('Croston, J.D., 1972.', ' https://doi.org/10.1057/jors.1972.50'),
    ('Friedman, J.H., 2001.', ' https://doi.org/10.1214/aos/1013203451'),
    ('Giannopoulos, P.G.', ' https://doi.org/10.1080/00207543.2025.2578701'),
    ('Hewamalage, H., Bergmeir', ' https://doi.org/10.1016/j.ijforecast.2020.06.008'),
    ('Hyndman, R.J., Koehler, A.B., 2006.', ' https://doi.org/10.1016/j.ijforecast.2006.03.001'),
    ('Januschowski, T., Gasthaus', ' https://doi.org/10.1016/j.ijforecast.2019.05.008'),
    ('Kapoor, S., Narayanan, A., 2023.', ' https://doi.org/10.1016/j.patter.2023.100804'),
    ('Kaufman, S., Rosset', ' https://doi.org/10.1145/2382577.2382579'),
    ('Kolassa, S., 2016.', ' https://doi.org/10.1016/j.ijforecast.2015.12.004'),
    ('Koning, A.J., Franses', ' https://doi.org/10.1016/j.ijforecast.2004.10.003'),
    ('Kourentzes, N., 2013.', ' https://doi.org/10.1016/j.ijpe.2013.01.009'),
    ('Kourentzes, N., 2014. On intermittent', ' https://doi.org/10.1016/j.ijpe.2014.06.007'),
    ('Kourentzes, N., Petropoulos, F., Trapero', ' https://doi.org/10.1016/j.ijforecast.2013.09.006'),
    ('Lim, B., Ar', ' https://doi.org/10.1016/j.ijforecast.2021.03.012'),
    ('Makridakis, S., Spiliotis, E., Assimakopoulos, V., 2020.', ' https://doi.org/10.1016/j.ijforecast.2019.04.014'),
    ('Makridakis, S., Spiliotis, E., Assimakopoulos, V., 2022.', ' https://doi.org/10.1016/j.ijforecast.2021.11.013'),
    ('Montero-Manso, P., Hyndman, R.J., 2021.', ' https://doi.org/10.1016/j.ijforecast.2021.03.004'),
    ('Nikolopoulos, K., Syntetos', ' https://doi.org/10.1057/jors.2010.32'),
    ('Oreshkin, B.N., Carpov', ' arXiv:1905.10437'),
    ('Petropoulos, F., Makridakis, S., Assimakopoulos, V., Nikolopoulos, K., 2014.', ' https://doi.org/10.1016/j.ejor.2014.02.036'),
    ('Petropoulos, F., et al., 2022.', ' https://doi.org/10.1016/j.ijforecast.2021.11.001'),
    ('Petropoulos, F., Kourentzes, N., 2015.', ' https://doi.org/10.1057/jors.2014.62'),
    ('Turrini, L., Meissner, J., 2021.', ' https://doi.org/10.1016/j.omega.2021.102513'),
    ('Salinas, D., Flunkert', ' https://doi.org/10.1016/j.ijforecast.2019.07.001'),
    ('Smyl, S., 2020.', ' https://doi.org/10.1016/j.ijforecast.2019.03.017'),
    ('Syntetos, A.A., Babai, M.Z., Boylan, J.E., Kolassa', ' https://doi.org/10.1016/j.ejor.2015.11.010'),
    ('Syntetos, A.A., Boylan, J.E., 2001.', ' https://doi.org/10.1016/S0925-5273(00)00143-2'),
    ('Syntetos, A.A., Boylan, J.E., 2005.', ' https://doi.org/10.1016/j.ijforecast.2004.10.001'),
    ('Syntetos, A.A., Boylan, J.E., Croston, J.D., 2005.', ' https://doi.org/10.1057/palgrave.jors.2601841'),
    ('Tashman, L.J., 2000.', ' https://doi.org/10.1016/S0169-2070(00)00065-0'),
    ('Teunter, R.H., Duncan, L., 2009.', ' https://doi.org/10.1057/palgrave.jors.2602569'),
    ('Teunter, R.H., Syntetos, A.A., Babai, M.Z., 2011.', ' https://doi.org/10.1016/j.ejor.2011.05.018'),
    ('Segerstedt, A., 2010.', ' https://doi.org/10.1016/j.ijpe.2010.07.013'),
    ('Willemain, T.R., Smart', ' https://doi.org/10.1016/S0169-2070(03)00013-X'),
    ('Zhang, G.P., Xia, Y., Xie, M., 2024.', ' https://doi.org/10.1007/s10479-023-05447-7'),
]

def _add_dois(refs):
    return [r + next((s for n, s in DOIS if n in r), '') for r in refs]

def _neural():
    """Load neural summaries if present; return (m5, or2) dicts or (None, None)."""
    out = {}
    for ds in ['m5', 'or2']:
        p = fr'{RES}\{ds}_neural_summary.json'
        out[ds] = json.load(open(p)) if os.path.exists(p) else None
    return out['m5'], out['or2']

def blocks(anonymous=False):
    B = []
    A = B.append
    # dynamic neural-summary numbers, consumed by the deep-forecaster subsection (5.5)
    m5n, or2n = _neural()
    A(('title', TITLE))
    if not anonymous:
        A(('authors', AUTHORS, AFFIL))

    A(('h_abstract', 'Abstract'))

    # Long-form abstract (544 words) used before the arXiv version. Kept for reference:
    # Demand forecasting is the analytical foundation of supply-chain planning: it sets the inventory,
    # replenishment, transportation and labour decisions that govern the cost and resilience of how goods
    # reach consumers. Two questions now dominate practice. First, does the recent turn to artificial
    # intelligence (AI), global machine-learning models trained jointly across thousands of products, actually
    # improve demand forecasts over the simple statistical methods embedded in most planning systems, and if
    # so, where? Second, can the in-sample fit statistics that planning dashboards use to choose a forecasting
    # method be trusted out-of-sample? We answer both on two openly available retail datasets that together
    # span the demand spectrum: the M5 competition data (30,490 Walmart store–SKU series, denser and partly
    # smooth) and the UCI Online Retail II data (4,675 e-commerce series, sparse and predominantly lumpy). We
    # re-implement Naive, moving-average, exponential-smoothing, Croston and Syntetos–Boylan (SBA)
    # forecasters, a gradient-boosted global model (LightGBM, the method class that won M5), and two deep
    # neural forecasters (NHITS and DeepAR), and evaluate all of them under an identical rolling-origin out-
    # of-sample (OOS) design with scale-free error metrics. We report four findings. (i) Method selection
    # inverts between in-sample and out-of-sample: the forecaster that looks best on the history used to fit
    # it is not the one that generalises. Most starkly, SBA wins the most series in-sample on Online Retail II
    # (47%) yet is beaten by a naïve random walk out-of-sample. (ii) Modern AI forecasters add genuine
    # accuracy, but which kind matters: the global LightGBM model is the best single method on the denser
    # panel (mean MASE 0.952 on M5), while on the sparse panel, once price features are restricted to strictly
    # past information, it is beaten by tuned exponential smoothing, and the deep global models (NHITS,
    # DeepAR) lead wherever series are long enough to train on: decisively by MASE, and at parity with tuned
    # smoothing under squared-error scoring. In documenting this we expose a subtle target leak of broad
    # practical relevance: a same-week transacted-price feature perfectly identifies sale weeks in
    # transactional data and silently inflated the gradient-boosted model’s apparent accuracy. (iii) The value
    # of AI is strongly conditional on demand regime and data sufficiency: decisive for higher-volume, denser,
    # longer demand histories, it collapses on the sparse, short, intermittent tail, where under MAE-based
    # scoring zero-forecasting simple methods take 61–65% of series wins and nothing beats a naïve benchmark;
    # a squared-error (RMSSE) sensitivity preserves the regime gradient and the leaders while exposing the
    # naive benchmark’s apparent strength as an artefact of median-rewarding metrics. (iv) Much of the
    # apparent weakness of the Croston family is an artefact of the one-step horizon on which such comparisons
    # are conventionally run, which is the least favourable way to score an estimator of a demand rate. Re-
    # scored on cumulative lead-time demand, Croston rises from fourth of five classical methods at one step
    # to second at a thirteen-week lead time and first at twenty-six on M5, while staying last at every
    # horizon on the sparse panel: evaluation design and demand regime interact. The results give planners an
    # evidence-based rule (match the forecaster to the demand regime, the metric to the decision and the
    # evaluation horizon to the replenishment cycle, validate out-of-sample, and audit feature timing) and
    # temper expectations that AI is a universal remedy for demand uncertainty. All data are public and all
    # code is released.

    A(('p', 'Comparisons between machine-learning and classical demand forecasters are read as statements '
            'about methods. They are also statements about the evaluation. We show that three individually '
            'defensible design choices each reverse the ranking on the same data, using two public retail '
            'datasets chosen to bracket the intermittency spectrum: the M5 competition data (30,490 store-SKU '
            'series) and UCI Online Retail II (4,675 e-commerce series). Eight classical forecasters, a global '
            'gradient-boosted model, two deep global models and two pretrained zero-shot models are evaluated '
            'under one rolling-origin design. Lengthening the evaluation horizon from one week to a '
            'twenty-six-week lead time moves Croston’s method from last of eight classical methods to '
            'first on the denser panel, its error against a naive benchmark falling from 1.005 to 0.568, while '
            'the sparse panel leaves Croston last at every lead time we test. Two things are therefore confounded in the '
            'received verdict on the Croston family: the one-step scoring that Teunter and Duncan (2009) '
            'warned about, and the family itself, since its third member TSB finishes third of the eight '
            'classical methods on the dense panel and fourth on the sparse one at one step with no change of '
            'horizon, while Croston and SBA finish in the bottom three of both. Restricting one price feature to strictly past values removes '
            'a silent target leak. A same-week transacted price identifies sale weeks perfectly and carries 42 '
            'percent of the model’s gain; without it the gradient-boosted model falls from ahead of every '
            'classical method to behind tuned exponential smoothing. Replacing MASE with RMSSE turns the naive '
            'benchmark from a method that wins more than a fifth of all series on the sparse panel, more than '
            'every forecaster there except a short moving average, into the method with the worst mean RMSSE '
            'on both. '
            'Method selection is subject to the same instability: on Online Retail II the Syntetos-Boylan '
            'Approximation wins the most series in-sample yet loses to a naive random walk out-of-sample. A '
            'test using two pretrained models that need no per-series history finds that neither beats the best '
            'trained '
            'trained model in any sparse demand class: the gap favours the trained model in all four, and a '
            'paired bootstrap clears zero in all four. What bounds accuracy on the sparse tail is therefore data sufficiency and not model '
            'class. Scoring predictive quantiles rather than point forecasts, the two Chronos-Bolt checkpoints also beat an '
            'empirical training-quantile benchmark by about 20% in scaled pinball loss, and doing so exposes a second '
            'limitation: the two Chronos-Bolt checkpoints we score are trained on deciles, so a request for the 99th '
            'percentile returns the 90th, clamped. The ceiling is documented and the library logs a warning, but '
            'the call still returns a number rather than raising, so a pipeline that does not read its logs '
            'silently reads a relabelled 90th percentile. For practice, the error metric has '
            'to match the loss the decision carries and the evaluation horizon has to match the replenishment '
            'cycle. Feature timing and the quantiles a model can express both need auditing before a '
            'machine-learning gain is believed. All data and code are public.'))

    A(('keywords', 'Keywords: Evaluation design; intermittent demand; Croston’s method; lead-time demand; '
        'forecast accuracy measures; data leakage; model selection; M5 competition.'))

    A(('h1', '1. Introduction'))
    A(('p', 'Few analytical tasks touch the physical economy as broadly as demand forecasting. The forecast for '
        'each product at each location is the input to almost every downstream supply-chain decision: how much '
        'to order, how much safety stock to hold, how to route and staff distribution, and when to mark down '
        'or discontinue. Errors are expensive in both directions: under-forecasting causes stock-outs, lost '
        'sales and expedited freight, while over-forecasting ties up working capital and, for perishables, '
        'produces outright waste. In the United States alone, total business inventories stood at $2.74 trillion in '
        'June 2026 (U.S. Census Bureau, 2026), and a material share of food moving through grocery supply chains '
        'is lost or wasted; even small proportional improvements in forecast accuracy translate into large '
        'absolute savings and reductions in waste and emissions. The resilience of supply chains has '
        'accordingly become an explicit policy priority (e.g., U.S. Executive Order 14017 on America’s Supply '
        'Chains, 2021), and forecasting quality is a quiet but decisive determinant of that resilience.'))
    A(('p', 'Against this backdrop the field is in the middle of a methodological shift. For decades, '
        'operational demand planning has relied on lightweight univariate statistical methods: exponential '
        'smoothing, moving averages, and, for the slow-moving items that dominate most catalogues, the Croston '
        'method and its Syntetos–Boylan Approximation (SBA). The 2020 M5 forecasting competition marked an '
        'inflection point: the top-ranked solutions were global machine-learning models, predominantly '
        'gradient-boosted trees, trained jointly across all series rather than one model fitted per series '
        '(Makridakis et al., 2022). This result has driven rapid adoption of “AI” forecasting in industry. Yet '
        'two practical questions remain inadequately answered for the planners who must act on these forecasts.'))
    A(('p', 'The first question is where, and by how much, machine learning actually helps. Competition leaderboards report a '
        'single aggregate score; they do not tell a planner whether the gain is uniform across the assortment '
        'or concentrated in particular kinds of demand. Much real supply-chain demand is intermittent (long '
        'runs of zero punctuated by sporadic, variable orders), precisely the regime in which flexible models '
        'have the least signal to exploit and simple methods are notoriously hard to beat. The second question '
        'is whether the basis on which methods are routinely chosen can be trusted. In practice the selection '
        'is frequently made on an in-sample error statistic computed over the same history used to fit the '
        'model and surfaced on a planning dashboard. Whether such in-sample rankings survive honest '
        'out-of-sample (OOS) testing is rarely examined on real data, even though the chosen method propagates '
        'directly into committed inventory.'))
    A(('p', 'This paper addresses both questions with a single, deliberately reproducible design, and in doing so '
        'arrives at a third question that subsumes them. We study two openly available retail datasets chosen to '
        'bracket the demand spectrum: the M5 dataset (dense, high-volume grocery; 30,490 store–SKU series) and '
        'the UCI Online Retail II dataset (sparse, lumpy e-commerce; 4,675 product series). On each we '
        're-implement eight classical forecasters, a global gradient-boosted model of the M5-winning class, two '
        'deep neural forecasters and two pretrained zero-shot foundation models, and we evaluate all of them '
        'under one identical rolling-origin OOS protocol with scale-free metrics. Holding the data, the '
        'forecasters and the protocol fixed, we then vary the evaluation design itself.'))
    A(('p', 'Our contributions are three claims and the benchmark that supports them. '
        '(i) Method rankings are not properties of methods alone. We exhibit three separate design choices, each '
        'individually defensible and each conventional somewhere in the literature, that reverse the ranking on '
        'the same data: the forecast horizon, the causality of a single feature, and the choice of error metric. '
        'The in-sample statistic that planning systems use for selection is a fourth such choice: on the sparse '
        'panel it crowns a method a naive random walk beats out of sample, and on the dense one it costs its '
        'champion two thirds of its win rate. A fifth, the range over which the classical methods are tuned, '
        'is examined in Section 5.13. '
        '(ii) The standing of the Croston family is in part an evaluation artefact rather than a property of the '
        'estimators. Scored on cumulative lead-time demand rather than one step ahead, Croston rises from last '
        'of eight classical methods to first on the denser panel. Teunter and Duncan (2009) argued that '
        'per-period error measures are the wrong instrument for intermittent demand; the size of the reversal '
        'that follows from changing the instrument is our result. On the sparse panel Croston stays last at '
        'every lead time, so evaluation design and demand regime '
        'interact rather than acting separately. The family also has to be disaggregated: TSB, which smooths a '
        'demand probability rather than an inter-demand interval, finishes third of the eight classical '
        'methods on the dense panel and fourth on the sparse one at one step, well clear of Croston and SBA, so '
        'the received verdict rests on scoring two particular members in the least favourable way. '
        '(iii) The data-sufficiency explanation for the failure of machine learning on sparse demand survives a '
        'direct falsification test. Two pretrained models that need no per-series history at all, and that '
        'therefore should not share the limitation if the binding constraint were per-series data volume, still '
        'do not beat trained models in any sparse demand class on either panel, and lose outright in all four '
        'once the gaps are given bootstrap intervals. '
        'Supporting these is a fully public, end-to-end reproducible pipeline spanning classical, '
        'gradient-boosted, deep-learning and pretrained forecasters, from raw public files to every table and '
        'figure. Section 2 reviews the literature; Section 3 describes the data; Section 4 the methods; '
        'Section 5 the results; Sections 6 and 7 discuss implications and conclude.'))

    A(('h1', '2. Literature review'))
    A(('h2', '2.1 Intermittent demand and its characterisation'))
    A(('p', 'Intermittent demand (sequences of zeros interrupted by occasional, often variable, positive '
        'orders) has been studied for half a century. Croston (1972) showed that applying exponential '
        'smoothing directly to such series is biased, and proposed decomposing demand into separately smoothed '
        'estimates of demand size and inter-demand interval. Syntetos and Boylan (2001) proved that Croston’s '
        'estimator is itself biased and introduced a multiplicative bias correction (a factor of 1 − α/2); the '
        'resulting Syntetos–Boylan Approximation (SBA) was assessed in Syntetos and Boylan (2005) and has '
        'become the de facto industry standard. Teunter, Syntetos and Babai (2011) extended the family with '
        'the TSB method, which updates the demand probability every period and so suits items at risk of '
        'obsolescence, while Willemain, Smart and Schwarz (2004) took a different route, using a time-series '
        'bootstrap to forecast the entire lead-time demand distribution rather than a point rate. For method '
        'selection, demand is commonly segmented: Syntetos, Boylan and Croston (2005) proposed cut-offs on the '
        'average inter-demand interval (ADI = 1.32) and the squared coefficient of variation of non-zero sizes '
        '(CV² = 0.49) that partition series into smooth, intermittent, erratic and lumpy regimes, a scheme '
        'embedded in most planning software and used here to structure the regime-conditional analysis.'))
    A(('h2', '2.2 Comparative studies and “horses for courses”'))
    A(('p', 'A large empirical literature compares intermittent-demand forecasters, and its conclusions are '
        'notably sensitive to data and evaluation design. Teunter and Duncan (2009), comparing methods on a '
        'large Royal Air Force service-parts data set, report two results that bear directly on the present '
        'study. Conventional per-period forecast error measures are inappropriate for intermittent demand, '
        'even though the literature uses them consistently. And when methods are judged by their ability to '
        'hit target service levels and by their stock-holding implications, Croston-type and bootstrap methods '
        'clearly outperform the moving average and simple exponential smoothing. They further show that '
        'Croston-type forecasts improve once the method itself accounts for an order in a period being triggered '
        'by a demand in that period. Our primary metric and our sensitivity metric are both per-period '
        'measures, so their warning applies to this study directly; Section 5.6 tests it. '
        'Babai, Syntetos and Teunter (2014) evaluated such methods on '
        'real data against both forecast accuracy and the risk of obsolescence. Most directly, '
        'Petropoulos, Makridakis, Assimakopoulos and Nikolopoulos (2014) articulated a “horses for courses” '
        'view in which forecasting performance is conditional on the features of the data, so that no single '
        'method dominates, a theme the present study extends to the classical-versus-machine-learning comparison. A '
        'complementary strand improves intermittent-demand forecasts through temporal aggregation, which '
        'dampens intermittence: the ADIDA approach of Nikolopoulos, Syntetos, Boylan, Petropoulos and '
        'Assimakopoulos (2011) aggregates demand into a single higher-level bucket. Aggregating at several '
        'levels at once generalises that step. The MAPA algorithm of Kourentzes, Petropoulos and Trapero '
        '(2014) combines multiple aggregation levels, though it was developed on regular series to reduce '
        'the burden of exponential smoothing model selection rather than to handle zeros; Petropoulos and '
        'Kourentzes (2015) carry the idea across to intermittent demand, where combinations across '
        'aggregation levels beat single methods applied to the original series.'))
    A(('h2', '2.3 Spare parts and supply-chain forecasting in practice'))
    A(('p', 'Because intermittent demand dominates service- and spare-parts inventories, a practitioner-facing '
        'literature studies how these forecasts are made and used. Pinçe, Turrini and Meissner (2021) provide '
        'a critical review of spare-parts demand forecasting, and Bacchetti and Saccani (2012) document a '
        'persistent gap between the methods proposed in research and those adopted in practice, where simple '
        'rules and built-in software statistics still prevail. Syntetos, Babai, Boylan, Kolassa and '
        'Nikolopoulos (2016) survey supply-chain forecasting as a whole and draw attention to exactly the '
        'theory–practice gap (including how methods are selected and evaluated) that motivates this study.'))
    A(('h2', '2.4 Error measurement and out-of-sample evaluation'))
    A(('p', 'Measuring accuracy is itself contested for intermittent demand. Percentage errors (e.g., MAPE) '
        'are undefined on the many zero actuals, and scale-dependent measures such as RMSE are dominated by a '
        'few high-volume items when aggregated across heterogeneous series; Hyndman and Koehler (2006) '
        'proposed the mean absolute scaled error (MASE) as a scale-free standard, which we adopt alongside the '
        'Percentage-Best measure that counts each series once. Wallström and Segerstedt (2010) caution that no '
        'single error statistic captures all dimensions of intermittent-demand error and recommend '
        'complementary measures, and Kolassa (2016) argues for evaluating entire discrete predictive '
        'distributions with proper scoring rules in low-count retail settings. On evaluation design, Tashman '
        '(2000) reviewed out-of-sample test design and recommended rolling-origin evaluation, with parameters '
        'estimated only on data preceding each forecast origin, which we follow; the encyclopaedic review of Petropoulos '
        'et al. (2022) synthesises this measurement and evaluation literature.'))
    A(('h2', '2.5 Machine learning, global models and forecasting competitions'))
    A(('p', 'Forecasting has shifted from local, per-series statistical models toward global machine-learning '
        'models trained jointly across many series. The dominant method class rests on gradient boosting of '
        'regression trees (Friedman, 2001), made scalable by XGBoost (Chen and Guestrin, 2016) and LightGBM '
        '(Ke et al., 2017). Competition evidence has been decisive: in the M4 competition of 100,000 series '
        '(Makridakis, Spiliotis and Assimakopoulos, 2020) the winning entry was a hybrid of exponential '
        'smoothing and a recurrent network (Smyl, 2020), and in the M5 retail competition (Makridakis et al., '
        '2022) the top-ranked solutions were predominantly LightGBM-based global models. Montero-Manso and '
        'Hyndman (2021) give theoretical and empirical grounds for why global models can match or beat local '
        'ones; Januschowski et al. (2020) argue that the “machine-learning versus statistical” dichotomy is '
        'less fundamental than commonly assumed; and Bojer and Meldgaard (2021), reviewing Kaggle forecasting '
        'competitions, report that their datasets have higher entropy than the M3 and M4 competitions and are '
        'intermittent, and that '
        'global ensemble models tend to outperform local single models.'))
    A(('h2', '2.6 Deep learning for demand forecasting'))
    A(('p', 'A parallel deep-learning literature supplies the neural forecasters we benchmark. DeepAR (Salinas '
        'et al., 2020) is a global autoregressive recurrent network producing probabilistic forecasts; N-BEATS '
        '(Oreshkin et al., 2020) is a deep stack of fully connected basis-expansion blocks that proved '
        'competitive with the M4 winner using no time-series-specific components; and NHITS (Challu et al., '
        '2023) improves N-BEATS’ efficiency and long-horizon accuracy through multi-rate sampling and '
        'hierarchical interpolation. The Temporal Fusion Transformer (Lim, Arık, Loeff and Pfister, 2021) adds '
        'attention and interpretability while combining static, known-future and observed inputs, and '
        'Hewamalage, Bergmeir and Bandara (2021) review recurrent networks for forecasting and the conditions '
        'under which they help. For intermittent demand specifically, Kourentzes (2013) proposed neural '
        'networks that forecast a dynamic rather than a constant demand rate, and found the accuracy and '
        'inventory verdicts on them to point in opposite directions: the networks scored poorly on '
        'conventional forecast accuracy and on bias, yet every variant reached a higher service level than '
        'the best Croston variant without a matching rise in stock holding, which led him to argue against '
        'conventional accuracy metrics for intermittent demand altogether. That is dependence on the choice '
        'of metric rather than on the demand regime, and it is a direct precedent for the metric reversal we '
        'report in Section 5.8. Most recently, attention-based architectures have '
        'been applied directly to intermittent series: Zhang, Xia and Xie (2024) report that a Transformer '
        'outperforms Croston/SBA and feed-forward, recurrent and LSTM baselines on 925 airline spare-parts '
        'series, and that its advantage over those baselines widens as demand grows sparser. That last result '
        'points the opposite way to the regime dependence we report in Section 5.4, where the advantage of '
        'flexible models narrows as demand sparsifies. The disagreement is worth taking seriously rather than '
        'attributing to noise, and the results of this paper let us name what could produce it.'))
    A(('p', 'Four candidate explanations are separable, and three of them we can now measure. Domain and '
        'demand profile is the obvious one: 925 items from a single aviation distributor against 35,165 '
        'series spanning all four SBC quadrants on two public retail panels, which differ in obsolescence, '
        'assortment turnover and the share of structural zeros. Less obvious is the composition of the '
        'classical baseline. Their classical comparators are Croston and SBA, and Section 5.3 shows those are '
        'the two weakest members of their own family under one-step scoring, while TSB, the third member, '
        'finishes third of the eight classical methods on the dense panel and fourth on the sparse one. A margin measured against Croston and SBA is not the same '
        'quantity as a margin against the best available classical method, so part of any reported gap may '
        'belong to the comparator rather than to the Transformer. The evaluation horizon is a third '
        'candidate. Section 5.6 shows that one-step scoring is precisely the design that suppresses '
        'Croston-type rate estimators, and that re-scoring on cumulated lead-time demand moves Croston from '
        'last of eight to first on our denser panel. Teunter and Duncan (2009) argued that per-period error '
        'measures are the wrong instrument for intermittent demand; the size of the reversal that follows '
        'from changing the instrument is our result, not theirs. The '
        'error measure is the fourth, since Section 5.8 shows that MASE and RMSSE agree on the winner but not on '
        'the ordering behind it, reversing the standing of the naive benchmark, '
        'and Section 6.1 that mean error and win-counting disagree in six of the eight demand cells. '
        'Hold-out length we can only partly rule out: Section 5.11 finds the classical ordering stable across '
        'three hold-out '
        'windows on each panel, so the size of the test window alone is unlikely to account for a reversal of '
        'this size.'))
    A(('p', 'This does not settle the disagreement, and it cannot be settled from either paper alone, since '
        'the two studies vary domain, baseline set, horizon and metric at the same time. That is the confound '
        'this paper is about. It is a designable experiment, though. Running both method sets on both kinds '
        'of data, under both evaluation designs and with TSB in the classical arm, would separate a domain '
        'effect from an evaluation effect and answer a question neither study can answer on its own. It is '
        'the extension of this work we would most like to see run. The rapidly growing use of machine '
        'learning for intermittent demand is surveyed by Giannopoulos, Dasaklis, Tsantilis and Patsakis '
        '(2025).'))
    A(('p', 'A newer line of work pretrains one model on large heterogeneous corpora of time series and then '
        'forecasts unseen series with no per-dataset training. Lag-Llama (Rasul et al., 2023) and TimeGPT '
        '(Garza, Challu and Mergenthaler-Canseco, 2023) were early entrants. Chronos (Ansari et al., 2024) '
        'quantises scaled series into tokens and trains a language-model architecture over them; TimesFM (Das '
        'et al., 2024) is a decoder-only patched forecaster; Moirai (Woo et al., 2024) handles arbitrary '
        'frequencies and covariate counts in a single model; and MOMENT (Goswami et al., 2024) provides a '
        'general-purpose family spanning forecasting and related tasks. These are a different comparison class '
        'from the global models benchmarked here, because they are never fitted to the panel under study. '
        'That makes them a direct test of the data-sufficiency argument. If machine-learning forecasters lose '
        'their edge on the sparse tail because each series carries too little history to learn from, then a '
        'model that needs no per-series history at all should not share the limitation. We therefore benchmark '
        'Chronos-Bolt and TimesFM zero-shot, under the same rolling-origin protocol as every other method, and '
        'report the result in Section 5.9.'))
    A(('h2', '2.7 Research gap'))
    A(('p', 'The literature reviewed above contains, in separate places, warnings that each of the design '
        'choices we vary can matter: Tashman (2000) on out-of-sample test design, Teunter and Duncan (2009) on '
        'scoring a rate estimator at one step, and Kolassa (2016) on the metric in low-count retail settings. '
        'What is rarely done is to hold a single comparison fixed and vary those choices within it, so that '
        'their effect on the ranking can be measured rather than assumed. Three gaps follow. First, whether the '
        'in-sample fit statistics used to select forecasters in practice survive out-of-sample testing is '
        'seldom examined at scale on real data, even though the selected method propagates into committed '
        'inventory. Second, the value of modern global machine-learning forecasters relative to classical '
        'methods has been measured mainly by single aggregate competition scores, leaving open where on the '
        'intermittency spectrum that value accrues and how much of it survives a change of evaluation design. '
        'Third, comparisons are seldom both reproducible on public data and conducted under one identical '
        'protocol spanning classical, gradient-boosted, deep-learning and pretrained methods, which is what '
        'makes varying the design informative rather than confounded. We address all three.'))

    A(('h1', '3. Data'))
    A(('p', 'We use two publicly available datasets so that every result in this paper can be reproduced '
        'exactly from open sources (Section 8). Both are aggregated to a weekly planning bucket, the natural '
        'cadence for retail replenishment, and each series is taken from its first observed sale to the end of '
        'the window so that intermittency reflects genuine demand sparsity rather than pre-launch absence.'))
    A(('table', ['Attribute', 'M5 (Walmart)', 'Online Retail II'],
        [['Source', 'M5 competition (Kaggle/IJF)', 'UCI Machine Learning Repository'],
         ['Domain', 'US grocery & general merch.', 'UK online gift retailer'],
         ['Series (store–SKU / SKU)', '30,490', '4,675'],
         ['Window (weekly)', '281 weeks (2011–2016)', '104 weeks (2009–2011)'],
         ['Panel observations', '6.81 million', '0.41 million'],
         ['Zero-demand weeks', '23.7%', '53.0%'],
         ['Median ADI / CV²', '1.25 / 0.32', '2.14 / 1.04'],
         ['Dominant SBC regime', 'Smooth (51.6%)', 'Lumpy (56.0%)'],
         ['Exogenous features', 'price, SNAP, event calendar', 'price, country']],
        [2.0, 2.3, 2.2], 'Table 1. The two public datasets, chosen to bracket the demand spectrum. M5 is '
        'denser and partly smooth; Online Retail II is sparse and predominantly lumpy.'))
    A(('p', 'For M5 we aggregate the daily store–SKU unit sales to canonical M5 weeks and retain the '
        'competition’s exogenous variables (weekly selling price, state SNAP days, and the holiday/event '
        'calendar). For Online Retail II we combine both annual sheets, remove cancelled invoices, returns and '
        'non-product service codes (e.g., postage, bank charges), and aggregate invoice lines to weekly units '
        'sold per stock code (1.01 million clean line items across 4,675 products). For the forecast comparison '
        'we retain series that are estimable: at least two non-zero training weeks; dead and single-event items '
        'are a stocking-policy problem, not a forecasting one.'))
    A(('p', 'Series are assigned to SBC demand classes on the training window only. The interval and variability statistics that define the class are computed from weeks strictly before the forecast origin, so no series is placed in a class on the strength of behaviour it is later scored on. Section 5.4 reports what the usual full-span convention does to the by-class results.'))
    A(('p', 'Both raw sources stop mid-week, and the consequence is larger than the detail sounds. The M5 calendar’s final bucket holds two days rather than seven, and the Online Retail II transaction window opens on a Tuesday and closes on a Friday, leaving its first bucket short a Monday and its last short a Sunday. Summing units into such a bucket produces a smaller week, not a weaker demand week, and nothing downstream can tell the difference: the forecaster is charged for an over-forecast it did not make. On M5 the effect is large enough to change a conclusion. The truncated week carries a panel mean of 3.195 units against 10.413 the week before, it falls inside the hold-out window, and leaving it there lifts the mean MASE of every method we score. The level-based forecasters, TSB among them, take about 0.025 of it and Croston and SBA roughly a third of that, enough to push tuned exponential smoothing from below the naive benchmark to exactly on it. We therefore keep only weeks the source data covers end to end, which drops one week from M5 and the two edge weeks from Online Retail II. We record the decision here because a results table cannot show it: it leaves no trace except in the conclusions.'))

    A(('h1', '4. Methods'))
    A(('h2', '4.1 Forecasters and parameterisation'))
    A(('p', 'All six classical methods are re-implemented from the raw weekly histories and warm-started from '
        'the training window: SES is initialised at the training mean; Croston and SBA at the training mean '
        'non-zero size and mean inter-demand interval, which avoids the well-known pitfall of seeding the '
        'interval at one period; and TSB at the training mean non-zero size and the training share of periods '
        'carrying demand. TSB (Teunter, Syntetos and Babai, 2011) differs from Croston and SBA in what it '
        'smooths and when: it replaces the inter-demand interval with a demand probability and updates that '
        'probability in every period, including periods of zero demand, so a series that stops selling decays '
        'toward zero instead of holding its last estimated rate. It is included because the sparse panel is '
        'exactly the obsolescence regime it was designed for. Per-series smoothing parameters are chosen by '
        'grid search minimising one-step training-window MAE (SES α∈{0.05,…,0.4}; Croston/SBA/TSB '
        'α∈{0.01,…,0.3}; SMA window k∈{2,3,4}). Two temporal-aggregation methods complete the classical arm. '
        'ADIDA (Nikolopoulos et al., 2011) aggregates demand into wider buckets, forecasts at the aggregate '
        'level and disaggregates back; we use overlapping aggregation, which is the variant that suits a '
        'rolling-origin one-step protocol, with SES at the aggregate level, equal-weight disaggregation, and '
        'a per-series grid over the bucket k∈{1,2,3,4,6,13} and α∈{0.05,…,0.4}. Offering k = 1, at which '
        'ADIDA reduces to SES exactly, lets the tuner decline to aggregate; Section 5.6 reports how often it '
        'does. MAPA (Kourentzes et al., 2014) '
        'combines rather than selects, averaging the ADIDA forecasts over k∈{1,2,3,4,6,13}; combination is '
        'the method, so MAPA carries no bucket hyperparameter and is tuned over α alone, exactly as SES is. '
        'At k = 1 ADIDA reduces to SES by construction, which fixes the scale of any aggregation gain. '
        'Selected parameters are then '
        'frozen. Two aspects of this are conservative with respect to the Croston family and should be stated. '
        'A single α smooths both the demand size and the inter-demand interval, whereas Kourentzes (2014) '
        'finds that separate parameters can help; and the same work argues that conventional accuracy metrics, '
        'MAE among them, are poor criteria for optimising intermittent-demand models and SBA in particular. '
        'Both choices keep the classical arm simple and comparable across methods, and both plausibly cost '
        'Croston and SBA some accuracy. Section 5.6 returns to this. '
        'The gradient-boosted forecaster is a single global LightGBM model with a Tweedie objective '
        '(appropriate for zero-inflated counts), trained across all series on lagged demand (1–52 weeks), '
        'rolling means/dispersion, weeks-since-last-demand, cyclical calendar terms, price features, and, '
        'where available, SNAP, event and product-hierarchy variables. Price requires care. M5 prices are '
        'posted weekly catalogue prices, set in advance of sales, so the price level itself may be used at '
        'week t. Its normaliser may not: a full-sample median is computed over the whole panel, test window '
        'included, and so looks across the forecast origin, and we therefore divide by an expanding median '
        'of the prices observed up to t. Online '
        'Retail II prices are transacted prices that exist only in weeks with a sale, so a same-week price '
        'feature (or any imputation flag) trivially reveals the target; the model therefore receives only the '
        'last transacted price through week t−1 (forward-filled), again normalised by an expanding median. '
        'No price feature on either panel uses information unavailable at the forecast origin. '
        'Section 5.7 quantifies the inflation this rule prevents. The neural forecasters (NHITS and '
        'DeepAR) are global models trained on the raw weekly series for a fixed budget of 500 steps '
        '(single-threaded and seeded, which renders training deterministic); the number of trees for '
        'LightGBM is chosen by early stopping on a validation band immediately preceding the test window. '
        'No test information enters training.'))
    A(('h2', '4.2 Rolling-origin out-of-sample design'))
    A(('p', 'Each series is split into a training window and a hold-out test window (primary: the final 26 '
        'weeks for M5, 14 weeks for Online Retail II). Forecasts are one-step-ahead: at each origin every '
        'method observes realised demand through the current week and predicts the next. Because the horizon '
        'is one step, every lag and rolling feature used by the machine-learning models at a test week is an '
        'actual past observation, so no forecaster sees a value the others could not have seen at that origin. '
        'The feature sets themselves are not identical: the gradient-boosted model additionally reads price '
        'and, on M5, the SNAP and event calendars, which is what a global model is for, and it reserves the '
        'last weeks of the training window as an early-stopping band, so it fits on a slightly shorter history '
        'than the classical methods. What is held identical is the origin and the information available at it. '
        'Parameters and trained models are held fixed at their training-estimated values. Robustness is '
        'assessed by repeating the exercise at three hold-out lengths per dataset.'))
    A(('h2', '4.3 Error metrics and the in-sample/out-of-sample contrast'))
    A(('p', 'For each series we compute OOS MAE, RMSE, mean error (bias) and MASE (MAE divided by the '
        'in-sample one-step Naive MAE; series with a zero scaling factor are excluded from MASE aggregation). '
        'We report mean and median MASE, the Percentage-Best win-rate, and the share of series over-forecast. '
        'Ties in Percentage-Best (frequent on sparse series, where several methods forecast exactly zero and '
        'attain identical error) are split fractionally, each of the k tied methods receiving 1/k of the win, '
        'so that no method is favoured by arbitrary ordering. Following M-competition practice we add a '
        'multiple-comparisons-with-the-best (MCB) analysis (Koning, Franses, Hibon and Stekler, 2005): '
        'methods are ranked per series by out-of-sample MASE and mean ranks are compared against the Nemenyi '
        'critical distance at the 5% level. Finally, because MAE-based measures are minimised by the '
        'per-series median, which is zero for most intermittent series, they structurally favour '
        'zero-forecasters and penalise mean-rate estimators (Kolassa, 2016); we therefore repeat the entire '
        'comparison under the squared-error RMSSE of the M5 competition (Makridakis et al., 2022), which '
        'divides each series’ out-of-sample RMSE by its in-sample one-step naive RMSE and whose optimum is '
        'the conditional mean (Section 5.8). '
        'To test whether in-sample selection misleads, we additionally compute, for the classical methods, the '
        'in-sample training-fit MAE of each per-series-selected model and the resulting in-sample PB, and '
        'compare them against the out-of-sample PB and mean MASE. The in-sample view is exactly what a '
        'planning dashboard reports.'))
    A(('p', 'One caveat is owed to the source we lean on for that choice. Kolassa (2016) goes further than '
        'the median argument we borrow from him: he holds that MAD, MASE and wMAPE are inherently unsuitable '
        'for count data, and that point forecasts alone are insufficient for the inventory decisions these '
        'forecasts feed, which require the whole predictive distribution. We use MASE regardless, for two '
        'reasons. It is the measure the intermittent-demand literature and the M competitions report on, so '
        'it is the only one under which our numbers can be set beside published results. And among point '
        'measures it is the one that survives the failure modes of the alternatives on this data, since '
        'percentage errors are undefined on the many zero actuals and scale-dependent measures are dominated '
        'by a handful of high-volume items when aggregated across heterogeneous series. The RMSSE sensitivity '
        'in Section 5.8 answers the median-against-mean half of the objection and leaves the rest standing, '
        'because RMSSE is also a point measure. Two of the forecasters benchmarked here, DeepAR and '
        'Chronos-Bolt, emit full predictive distributions, and we score only their point output. Repeating '
        'the comparison under a proper scoring rule such as CRPS, or at the service-level quantiles an '
        'inventory policy actually reads, would meet Kolassa’s objection directly. Section 5.12 takes the '
        'second of those steps on the sparse panel, scoring the methods that emit native quantiles at levels a '
        'stocking decision reads. A full proper-scoring-rule comparison, extended to M5 and to the trained '
        'neural models, is still undone and is the most substantive gap in this study.'))


    A(('h1', '5. Results'))
    A(('h2', '5.1 Two datasets that bracket the demand spectrum'))
    A(('p', 'The two panels are deliberately different (Figure 1, Table 1). At the weekly bucket M5 is '
        'comparatively dense: 23.7% of weeks are zero, the median ADI is 1.25, and 51.6% of series fall in the '
        'smooth regime, with 42% intermittent or lumpy. Online Retail II is the opposite: 53.0% of weeks are '
        'zero, the median ADI is 2.14 with a high median CV² of 1.04, and 68% of series are intermittent or '
        'lumpy with only 4.5% smooth. Together they let us ask whether machine learning helps on average and where '
        'on the spectrum its help is real.'))
    A(('figure', 'fig1_fingerprint.png',
        'Figure 1. Demand fingerprints. M5 (left) is dense and partly smooth; Online Retail II (right) is '
        'sparse and predominantly lumpy. Dashed lines mark the SBC cut-offs (ADI = 1.32, CV² = 0.49).'))

    A(('h2', '5.2 In-sample selection inverts out-of-sample'))
    A(('p', 'Method rankings computed on the history used to fit the models do not survive honest '
        'out-of-sample testing (Figure 2, Table 2). On Online Retail II the inversion is textbook: SBA, the '
        'dedicated intermittent-demand estimator, wins the most series in-sample (39.4% Percentage-Best, more '
        'than twice the share of any other classical method), yet out-of-sample its win-rate falls to 16.0% '
        'and its mean MASE (1.088) is worse than a naïve random walk (0.957); out-of-sample it is the '
        'zero-forecasting simple pair, the short moving average and Naive, that take the most wins '
        '(25.4% and 22.3%). M5 inverts differently rather than less. Its in-sample champion is ADIDA '
        '(28.3% PB, ahead of the moving average at 20.3% and TSB at 16.9%), and out-of-sample ADIDA keeps a '
        'good mean error, second best of the eight at 0.976, while losing more than two thirds of its wins, '
        'down to 8.6%. The method that wins the most M5 series out-of-sample is SBA at 21.5%, which is '
        'sixth of eight on mean MASE. In both datasets the '
        'methods that fit the training history most flexibly are not those that generalise. The comparison '
        'also separates the intermittent-demand family internally: Croston and SBA rank among the worst '
        'methods out-of-sample by mean MASE despite SBA’s favourable in-sample appearance, whereas TSB, the '
        'obsolescence-aware member of the same family, is third on M5 and fourth on Online Retail II (0.985 '
        'and 0.847), ahead of Croston by 0.161 and 0.268 respectively. Selecting a forecaster on an in-sample '
        'dashboard statistic is therefore actively '
        'misleading, and so is treating "the Croston family" as a single thing.'))
    A(('figure', 'fig2_inversion.png',
        'Figure 2. The in-sample → out-of-sample inversion in Percentage-Best for the classical methods. The '
        'in-sample champion (highlighted) loses its lead under rolling-origin evaluation on both datasets.'))
    A(('table', ['Method', 'M5 in-samp PB%', 'M5 OOS MASE', 'M5 OOS PB%', 'OR2 in-samp PB%', 'OR2 OOS MASE', 'OR2 OOS PB%'],
        [['Naive', '6.3', '1.140', '12.1', '16.3', '0.957', '22.3'],
         ['SMA', '20.3', '1.005', '15.3', '16.7', '0.866', '25.4'],
         ['SES', '10.8', '0.974', '6.0', '3.2', '0.835', '5.0'],
         ['Croston', '2.0', '1.146', '11.5', '0.2', '1.115', '4.5'],
         ['SBA', '14.2', '1.138', '21.5', '39.4', '1.088', '16.0'],
         ['TSB', '16.9', '0.985', '10.1', '10.2', '0.847', '5.4'],
         ['ADIDA', '28.3', '0.976', '8.6', '13.6', '0.844', '8.6'],
         ['MAPA', '1.3', '0.996', '14.9', '0.3', '0.841', '12.7']],
        [1.0, 1.05, 0.95, 0.95, 1.05, 0.95, 0.95],
        'Table 2. The inversion, classical methods only. In-sample Percentage-Best (PB) versus out-of-sample '
        'mean MASE and PB; both PB columns are computed among these eight classical methods, with ties split '
        'fractionally (Section 4.3). Note SBA on Online Retail II: best in-sample (39.4%), beaten by the '
        'naïve random walk out-of-sample (MASE 1.088 vs 0.957). TSB separates from the other two members of '
        'the Croston family on both panels.'))

    A(('h2', '5.3 The machine-learning advantage is decisive on the dense panel and vanishes on the sparse one'))
    A(('p', 'Adding the global LightGBM model to the comparison, on M5 it is the best single '
        'forecaster: lowest mean MASE (0.936), lowest median (0.808) and a 36.2% nine-way Percentage-Best; '
        'see Table 3 and Figure 3. The gain '
        'over well-tuned exponential smoothing is real but modest, about 4% of mean MASE, and is bought with '
        'substantially greater modelling complexity. Four classical methods also finish below MASE 1 on this '
        'panel (SES at 0.974, ADIDA at 0.976, TSB at 0.985 and MAPA at 0.996), so clearing the naive scaling '
        'benchmark is not in itself the machine-learning result it can be made to look like; what separates '
        'the global model here is the size of the margin rather than the fact of one. On Online Retail II the '
        'picture reverses: with price '
        'information restricted to strictly past values (Sections 4.1 and 5.7), the global model records a '
        'mean MASE of 0.868, better than Naive (0.957) and far better than Croston and SBA, but behind tuned '
        'SES (0.835), MAPA (0.841), ADIDA (0.844), TSB (0.847) and the short moving average (0.866), and it '
        'wins only 9.7% of series. '
        'Cross-series gradient boosting, for all its M5 pedigree, does not by itself beat disciplined simple '
        'smoothing on a sparse, lumpy catalogue.'))
    A(('p', 'The classical arm also has to be read at the level of the individual estimator rather than the '
        'family. At this one-step horizon, and under MAE-based scoring, Croston and SBA are the weakest '
        'methods on Online Retail II, beaten even by Naive, and on M5 they occupy the bottom three places with '
        'the naive forecast between them, Croston last at 1.146 and SBA sixth at 1.138. TSB '
        'is the same family and behaves entirely differently: 0.985 on M5 and 0.847 on Online Retail II, '
        'third and fourth of the eight classical methods and ahead of the gradient-boosted model on the '
        'sparse panel. The '
        'difference is structural. Croston and SBA update only on demand periods, so a series that goes quiet '
        'keeps its last estimated rate indefinitely, whereas TSB updates the demand probability every period '
        'and decays toward zero through a run of zeros. Two of the three published members of the family are '
        'therefore weak here for a reason that is specific to their recursion, not to the idea of separating '
        'demand size from demand frequency. What remains of the Croston and SBA deficit is largely a horizon '
        'effect: Section 5.6 shows that on M5 Croston rises from last of eight classical methods to fifth at a quarterly '
        'lead time, and to first of the eight at 26 weeks, while on Online Retail II it remains last at every '
        'lead time we test. SBA additionally carries a large systematic under-forecast bias on M5 (it '
        'over-forecasts only 24.4% of series), which is what over-correction of the positive bias SBA was '
        'designed to remove would produce, and which is a liability for service-level planning.'))
    A(('figure', 'fig3_overall_mase.png',
        'Figure 3. Out-of-sample mean MASE for the nine core forecasters. The global machine-learning model (navy) is lowest '
        'on M5; on Online Retail II, with strictly causal features, tuned simple smoothing leads it. '
        'Croston/SBA are weakest on both at this one-step horizon; Section 5.6 shows that ordering changes on '
        'M5 as the lead time lengthens. The dashed line is the naïve benchmark (MASE = 1).'))
    A(('table', ['Method', 'M5 mean MASE', 'M5 med MASE', 'M5 PB%', 'OR2 mean MASE', 'OR2 med MASE', 'OR2 PB%'],
        [['Naive', '1.140', '1.001', '8.0', '0.957', '0.443', '21.5'],
         ['SMA', '1.005', '0.864', '10.0', '0.866', '0.403', '23.6'],
         ['SES', '0.974', '0.836', '3.0', '0.835', '0.450', '4.4'],
         ['Croston', '1.146', '0.888', '8.0', '1.115', '0.737', '3.8'],
         ['SBA', '1.138', '0.889', '15.1', '1.088', '0.706', '13.8'],
         ['TSB', '0.985', '0.837', '5.1', '0.847', '0.512', '4.4'],
         ['ADIDA', '0.976', '0.838', '5.7', '0.844', '0.458', '7.6'],
         ['MAPA', '0.996', '0.846', '8.9', '0.841', '0.465', '11.2'],
         ['LightGBM (global)', '0.936', '0.808', '36.2', '0.868', '0.499', '9.7']],
        [1.15, 1.0, 0.95, 0.85, 1.05, 0.95, 0.85],
        'Table 3. Out-of-sample accuracy, nine core methods, primary split (n = 30,460 M5; 4,284 OR2). PB is '
        'the nine-way Percentage-Best by MAE with fractional tie-splitting. The machine-learning model leads '
        'every aggregate on M5; on Online Retail II it trails tuned simple smoothing, TSB and both '
        'temporal-aggregation methods.',
        {'bold_last_row': True}))

    A(('h2', '5.4 The value of machine learning is conditional on the demand regime'))
    A(('p', 'The aggregate results conceal a sharp structural pattern that is the central practical message '
        'of this study (Figures 4–5). Disaggregating by SBC class and by out-of-sample demand volume shows '
        'that the machine-learning model’s advantage is concentrated in dense, higher-volume demand and fades on '
        'the sparse tail. On M5 the LightGBM win-rate climbs steadily with demand volume, from 8% in the '
        'lowest-volume decile, where a short moving average wins, to a peak of 48% in the ninth '
        'decile, holding at 48% in the highest-volume decile. On Online Retail II the structure is entirely different. The three lowest-volume deciles '
        'consist of items with zero realised demand in the test window, which every method that forecasts '
        'exactly zero "predicts" perfectly; with ties split fractionally, Naive and SMA share most '
        'of those wins (about 42% and 39% each). In the mid-volume bands it is SBA, not the machine-learning model, that '
        'attains the highest win-share (21–28%), precisely the recurring-intermittent niche for which it was '
        'designed, while the machine-learning model becomes competitive only in the top deciles (19–25%). By demand class, '
        'Naive and SMA jointly win 51% of Online Retail II’s intermittent and 55% of its lumpy series, and on '
        'M5 no method, including the machine-learning model, drives mean MASE below 1 on the intermittent or lumpy segments. By '
        'MAE-based win-counting, then, the hardest and sparsest part of the assortment looks unforecastable '
        'from its own history. That reading turns out to depend heavily on both the metric and the panel. '
        'Section 5.8 shows what changes under squared-error scoring, and Section 5.9 shows that on Online '
        'Retail II the deep and pretrained models cut mean MASE on the intermittent class by 27% against the '
        'best simple method, so by that measure the tail is a long way from unforecastable.'))
    A(('p', 'Every number in this section rests on a methodological choice that belongs in the text and not in a footnote. A series’s demand class is itself an evaluation-design choice. We compute the average inter-demand interval and the squared coefficient of variation from the training window alone, so that class membership cannot depend on the data the method is being scored against. The common convention is to compute them over the whole series, which looks harmless because a class describes a series and does not forecast it. On these panels it is not. Classifying over the full span moves 7.2% of M5 series and 6.1% of Online Retail II series into a different class, and it moves the class means by far more than that share suggests, because the series that move are exactly the ones whose activity changes across the forecast origin, and those carry the extreme scaled errors. Online Retail II’s intermittent class is the clearest case: under full-span classification tuned exponential smoothing records a mean MASE of 0.541 there, and under training-window classification it records 1.173. The class has not become harder to forecast; it has stopped excluding the hard cases. Sixty-two series enter it once the hold-out is no longer consulted; they average 16.6 active weeks in training and 21.3 units a week in the hold-out, against 0.64 for the series that were already there, and their mean MASE under exponential smoothing is 6.04 against 0.52. They are items that go quiet and then wake up, and a full-span classifier reads the waking up and files them somewhere else. The bias does not run one way: on M5’s lumpy class the full-span label was the pessimistic one (1.319 against 1.096), because it had pulled in 352 series averaging 2.98. What is consistent is that the taxonomy used to stratify a comparison can be contaminated by the comparison’s own test data, which is the same failure this paper documents for features in Section 5.7 and for the evaluation horizon in Section 5.6, applied to the labels instead of the methods.'))
    A(('figure', 'fig4_by_class.png',
        'Figure 4. Percentage-Best by SBC demand class (ties split fractionally). The machine-learning model dominates every M5 '
        'class; on Online Retail II’s sparse intermittent/lumpy classes the zero-forecasting simple methods '
        'take most wins.'))
    A(('figure', 'fig5_by_volume.png',
        'Figure 5. Percentage-Best across out-of-sample demand-volume deciles. On M5 the machine-learning model’s win-share '
        'rises steeply and then flattens across the top three deciles; on Online Retail II the simple methods own the zero tail '
        'and SBA peaks in its designed mid-volume niche.'))
    A(('table', ['SBC class', 'M5 SES', 'M5 SBA', 'M5 TSB', 'M5 ML',
                 'OR2 SES', 'OR2 SBA', 'OR2 TSB', 'OR2 ML'],
        [['Smooth', '0.826', '0.903', '0.832', '0.790', '1.171', '1.245', '1.249', '1.180'],
         ['Intermittent', '1.206', '1.512', '1.225', '1.165', '1.173', '1.558', '1.117', '1.310'],
         ['Erratic', '0.767', '0.839', '0.774', '0.727', '0.792', '0.818', '0.819', '0.809'],
         ['Lumpy', '1.096', '1.288', '1.100', '1.050', '0.755', '1.105', '0.770', '0.776']],
        [1.25, 0.8, 0.8, 0.8, 0.8, 0.85, 0.85, 0.85, 0.8],
        'Table 4. Mean OOS MASE by demand class (selected methods). The machine-learning model leads every '
        'regime on M5, and every method there exceeds MASE = 1 on intermittent and lumpy demand. On Online '
        'Retail II, with strictly past price information, simple exponential smoothing leads three of the four '
        'classes shown, while on the intermittent class TSB (1.117) is ahead of it (1.173) and of '
        'the machine-learning model (1.310), and is the best of all nine methods there. The gap between TSB '
        'and SBA on the sparse '
        'classes (1.117 against 1.558 intermittent, 0.770 against 1.105 lumpy) is the largest within-family '
        'difference anywhere in the study. The two temporal-aggregation methods are omitted from this table '
        'for width and are reported in Tables 2, 3, 5, 7, 8 and 9 and discussed in Section 5.6; on Online '
        'Retail II’s intermittent class MAPA is second of the nine (1.142), behind TSB and ahead of '
        'SES.'))

    A(('h2', '5.5 Do deep neural forecasters change the picture?'))
    if m5n and or2n:
        def g(d, m): return d['subset_comparison_mean_median'][m]
        rows = []
        for m in ['SES', 'LightGBM', 'NHITS', 'DeepAR']:
            rows.append([m if m != 'LightGBM' else 'LightGBM (global)',
                         f"{g(m5n,m)[0]:.3f}", f"{g(m5n,m)[1]:.3f}",
                         f"{g(or2n,m)[0]:.3f}", f"{g(or2n,m)[1]:.3f}"])
        m5_sub, or2_sub = m5n['subset_n'], or2n['subset_n']
        A(('p', 'A natural concern is whether deep learning, rather than gradient boosting, would overturn the '
            'regime-conditional conclusion. We therefore add two global neural forecasters, NHITS (an efficient '
            'N-BEATS-family model) and DeepAR (an autoregressive recurrent network), under the identical '
            'one-step rolling-origin protocol. Because a neural sequence model requires an input window of '
            'history, they can only be applied to series with sufficient length (here, at least input-window '
            f'+ horizon weeks: {m5_sub:,} M5 and {or2_sub:,} Online Retail II series qualify). On that common '
            'eligible subset, evaluated identically for every method, the neural models match the '
            'gradient-boosted model on M5 and are clearly the strongest methods by MASE on the longer Online '
            'Retail II histories, ahead of both LightGBM and the best classical method (Table 6); under the '
            'squared-error RMSSE of Section 5.8 their margin over tuned smoothing narrows to parity. Where '
            'cross-series learning genuinely pays on sparse data, it is the deep global models that deliver '
            'what gain there is. '
            'This does not weaken the central finding. It sharpens it. The very thing '
            'neural models need (a sufficiently long, information-rich history per series) is precisely what the '
            'sparse intermittent tail lacks, so the most complex models are the least applicable exactly where '
            'demand is hardest. By demand class on the eligible Online Retail II subset, NHITS attains a mean '
            f'MASE of {or2n["by_class"]["Intermittent"]["NHITS"]:.3f} on intermittent and '
            f'{or2n["by_class"]["Lumpy"]["NHITS"]:.3f} on lumpy series, strong where history exists, but mute on '
            'the short, near-dead items that simple methods and inventory policy must still handle. Deep '
            'learning thus extends, rather than contradicts, the data-sufficiency view of when machine learning pays off.'))
        A(('table', ['Method (eligible subset)', 'M5 mean', 'M5 median', 'OR2 mean', 'OR2 median'],
            rows, [2.2, 1.05, 1.05, 1.05, 1.05],
            f'Table 6. Mean / median OOS MASE on the neural-eligible subset (series with adequate history; '
            f'n = {m5_sub:,} M5, {or2_sub:,} OR2), every method scored on the same series. Neural models are '
            f'competitive with the gradient-boosted model and strongest on the longer histories.'))
    else:
        A(('p', '[Neural-baseline results pending: run 10_neural_baselines.py for both datasets.]'))

    A(('h2', '5.6 Design demonstration I: the forecast horizon reverses the Croston ranking'))
    A(('p', 'Croston and SBA do not produce a point forecast for a single period. They produce an estimate of '
        'the demand rate, the mean size divided by the mean inter-demand interval, and the quantity an '
        'inventory system consumes is that rate cumulated over a replenishment lead time. Scoring a rate '
        'against one realised week is therefore the least favourable way to assess it, which is the substance '
        'of the Teunter and Duncan (2009) warning discussed in Section 2.2. Because every ranking reported so '
        'far rests on a one-step horizon, we re-score the classical methods on cumulative L-week demand.'))
    A(('p', 'The eight classical forecasters all have a flat forecast function, a level or a rate, so the '
        'cumulative L-step forecast from origin t is L times the one-step forecast for t+1. For each origin in '
        'the hold-out window we compare that against realised demand summed over the next L weeks, counting '
        'only fully observed blocks, and scale each series by the in-sample MAE of a naive forecast of L-block '
        'cumulative demand. The gradient-boosted and neural models are one-step models and cannot be extended '
        'to a lead time without recursive simulation, so this sensitivity covers the classical arm only, which '
        'is where the disputed ranking sits. Absolute values are not comparable across lead times because the '
        'scaling denominator is recomputed at each L; rankings within a row are, and so are ratios to the '
        'naive benchmark.'))
    A(('p', 'The result is an asymmetry between the two panels (Table 9). On M5 the one-step ranking '
        'substantially understates Croston and SBA. Croston moves from last of eight at one step to fifth '
        'at a quarterly lead time and first at 26 weeks, and its error relative to the naive benchmark falls '
        'monotonically from 1.005 to 0.823 at four weeks, 0.672 at thirteen and 0.568 at twenty-six. At one '
        'step it is indistinguishable from a random walk, which is what Section 5.3 reports; at a realistic '
        'lead time it beats that benchmark by a third or more. The best classical method changes hands as the '
        'horizon lengthens, from SES at one to four weeks, to MAPA at eight and thirteen (4.353 and 6.785, '
        'with TSB within 0.004 of it at eight), to Croston at twenty-six, so the horizon effect is not '
        'confined to the two '
        'estimators that look worst at h = 1. On Online Retail II the picture does not change: Croston is '
        'last of eight at every lead time from one to fourteen weeks and never beats the naive forecast, its '
        'ratio moving only from 1.165 to 1.029. The longest lead time on each panel rests on a single fully '
        'observed block per series, so the 13-week M5 row, which has fourteen origins, is the defensible '
        'one.'))
    A(('p', 'Temporal aggregation dampens intermittency by widening the bucket, so it might be expected to '
        'reach the same place as lengthening the evaluation horizon. It does not, and the size of the gap is '
        'the useful part. ADIDA and MAPA are ordinary classical performers in aggregate: 0.976 and 0.996 on '
        'M5 and 0.844 and 0.841 on Online Retail II, in both cases behind tuned SES and never first '
        '(Table 3). The per-series tuner is explicit about why. ADIDA is offered the bucket k = 1, at which '
        'it reduces to SES exactly, and it takes that option on 65.2% of M5 series and 60.1% of Online '
        'Retail II series: given the choice, it declines to aggregate on roughly two series in three, and '
        'its aggregate mean converges toward SES because it is so often choosing SES. Where aggregation does '
        'pay is where the theory says it should, and nowhere else. On Online Retail II’s intermittent class '
        'MAPA (1.142) is second of the nine, ahead of SES (1.173) '
        'and far ahead of the gradient-boosted model (1.310), though it is beaten there by TSB (1.117), so '
        'aggregation is not even the best answer in the one regime built for it; on M5, whose sparse classes '
        'are sparse in a '
        'different way, aggregation never beats SES in any class and at best ties it, at 1.206 on the '
        'intermittent series and 0.767 on the erratic ones. So aggregation is a regime-specific remedy, '
        'and it is not a substitute for the horizon change. Re-scoring Croston on cumulated demand moves it '
        'by 44% of the naive benchmark, whereas aggregating inside the forecaster leaves the best '
        'aggregation method within one percent of SES on both panels and on the wrong side of it, and '
        'leaves Croston last on the sparse panel at every lead time we '
        'test. The horizon result is a statement about the evaluation, not a slower route to a modelling fix '
        'that could have been made instead.'))
    A(('p', 'Three conclusions follow, and all three sharpen rather than soften this paper. First, the claim '
        'that Croston and SBA are simply weak forecasters does not survive: on the denser panel their '
        'standing is largely an artefact of a one-step, MAE-based evaluation, exactly as Teunter and Duncan '
        'predicted. Second, the correction is itself regime-conditional. Lengthening the horizon rescues them '
        'where demand is dense enough for a rate estimate to be worth cumulating, and does nothing for it on '
        'the sparse, lumpy catalogue where the rate is estimated from too few events. Third, the horizon is '
        'not the only thing that was doing the damage: TSB, the same family with a probability recursion '
        'instead of an interval recursion, finishes third of the eight classical methods on M5 and fourth on '
        'Online Retail II at one step (Section 5.3) without '
        'any change of horizon at all. A verdict widely read as being about a family of estimators turns out '
        'to depend both on how they are scored and on which member of the family is scored. Evaluation design '
        'and demand regime interact, which is the same lesson Sections 5.4 and 5.8 draw for model complexity '
        'and for the choice of metric.'))
    A(('table',
        ['Panel and lead time', 'Naive', 'SMA', 'SES', 'Croston', 'SBA', 'TSB', 'ADIDA', 'MAPA',
         'Croston rank'],
        [['M5, L = 1', '1.140', '1.005', '0.974', '1.146', '1.138', '0.985', '0.976', '0.996', '8 of 8'],
         ['M5, L = 4', '3.563', '2.677', '2.458', '2.934', '2.947', '2.475', '2.471', '2.487', '6 of 8'],
         ['M5, L = 13', '10.512', '7.829', '6.884', '7.064', '7.147', '6.809', '6.948', '6.785', '5 of 8'],
         ['M5, L = 26', '21.249', '15.643', '13.487', '12.072', '12.230', '13.040', '13.586', '12.709', '1 of 8'],
         ['OR2, L = 1', '0.957', '0.866', '0.835', '1.115', '1.088', '0.847', '0.844', '0.841', '8 of 8'],
         ['OR2, L = 4', '3.337', '2.846', '2.632', '3.633', '3.562', '2.678', '2.667', '2.668', '8 of 8'],
         ['OR2, L = 7', '5.343', '4.557', '4.089', '5.708', '5.617', '4.143', '4.128', '4.117', '8 of 8']],
        [1.4, 0.8, 0.8, 0.8, 0.85, 0.8, 0.8, 0.8, 0.8, 1.0],
        'Table 9. Horizon sensitivity for the classical methods: mean scaled error on cumulative L-week '
        'demand, same eligibility as Table 3 (n = 30,460 M5 and 4,284 OR2 at L = 1, falling slightly as L '
        'grows because only fully observed blocks are scored). Values are comparable within a row, not down a '
        'column. On M5 Croston rises from last of eight to first as the lead time lengthens, and the best '
        'classical method changes hands from SES to MAPA and finally to Croston; on Online Retail II '
        'Croston stays last throughout. The temporal-aggregation methods move very little with the horizon, '
        'which is the contrast drawn in the text. Produced by code/22_leadtime.py.'))

    A(('h2', '5.7 Design demonstration II: feature timing reverses the machine-learning ranking'))
    A(('p', 'Feature-importance analysis clarifies why the gains take the shape they do (Figure 6, right). On '
        'both datasets the LightGBM model is driven overwhelmingly by recent-demand aggregates (short and '
        'medium rolling means, the expanding mean, the most recent lag) plus mild calendar seasonality. The '
        'concentration is extreme: on M5 the four-week rolling mean alone carries 66% of total gain, the four '
        'recent-demand features together carry 94%, and the two price variables carry 0.8% between them. The '
        'model’s edge, where it has one, comes from flexibly '
        'combining a smoothed recent-demand signal with these covariates; where demand is mostly zeros there '
        'is little signal to exploit and the model has nothing with which to beat a simple benchmark. The '
        'mechanism and the regime-conditional result are two sides of the same coin.'))
    A(('p', 'The price features deserve a cautionary note that we believe generalises beyond this study. Our '
        'initial Online Retail II specification used the same-week mean transacted price, the obvious default '
        'when, as in most transactional datasets, no posted catalogue price exists. Because a transacted '
        'price is recorded only when a sale occurs, that feature identifies sale weeks by its mere presence. '
        'The identity is structural rather than incidental: weekly price is aggregated from the same '
        'transaction rows as weekly demand and then joined onto a complete series grid, so P(y > 0 | price '
        'observed) = 1 holds on any window of this panel by construction, and we confirm it with no '
        'exceptions across all 407,702 series-weeks. Under that specification the two price variables '
        'carried 42% of the model’s total gain and ranked first and second among all twenty-one features, '
        'with a static full-window median price adding a further 2%. Set against the 0.8% the same two '
        'variables carry on M5, where prices are posted in advance and so cannot reveal the target, that 42% '
        'is itself the signature of the leak rather than evidence of genuine price response. The leak '
        'inflated the global model’s apparent accuracy from a mean MASE of 0.868 to 0.678, enough to move it '
        'from behind five of the eight classical methods to ahead of all eight. Restricting price to '
        'This failure mode is well documented outside forecasting. Kaufman, Rosset, Perlich and Stitelman '
        '(2012) formalise leakage as the introduction of information about the target that would not be '
        'legitimately available at prediction time, and identify this pattern, a feature whose presence '
        'is itself informative, as one of its recurring forms; Kapoor and Narayanan (2023) find 22 reviews '
        'across seventeen fields documenting errors in machine-learning-based science, collectively '
        'affecting 294 papers, with leakage among the recurring causes. What the present case adds is a demand-forecasting instance in which the '
        'leaking feature is the one a domain expert would reach for first. Restricting price to '
        'strictly lagged values (Section 4.1) removes the artefact; all Online Retail II results in this '
        'paper use the corrected specification, and the discarded one is retained behind a flag in the '
        'replication code so that the counterfactual regenerates rather than having to be taken on trust. '
        'Benchmarks that feed same-period transactional covariates to '
        'machine-learning forecasters will systematically overstate the value of machine learning, and the error is silent: '
        'nothing in the training pipeline fails, accuracy simply improves for the wrong reason.'))
    A(('figure', 'fig6_robustness.png',
        'Figure 6. Left and centre: mean OOS MASE by hold-out horizon. The classical ordering is stable across '
        'splits. Right: LightGBM feature importance on M5. Recent-demand aggregates dominate, with the '
        'four-week rolling mean alone at 66% of total gain and both price variables together at 0.8%.'))

    A(('h2', '5.8 Design demonstration III: the error metric reverses the benchmark ranking'))
    A(('p', 'MAE-based measures such as MASE are minimised by the per-series median, zero for most '
        'intermittent series, so they structurally reward zero-forecasters and penalise estimators of the '
        'mean demand rate, the functional that inventory calculations actually consume (Kolassa, 2016). '
        'Table 8 therefore repeats the comparison under the squared-error RMSSE. Three conclusions are '
        'metric-robust. LightGBM’s dominance of M5 strengthens (mean RMSSE 0.789; mean rank 3.06; best in '
        'all four demand classes), with TSB the best-ranked classical method behind it (3.98). Tuned simple '
        'smoothing still leads Online Retail II (SES 0.654, best under both metrics), with the two '
        'temporal-aggregation methods next (ADIDA 0.657, MAPA 0.660), TSB fourth (0.665) and the leak-free '
        'LightGBM fifth '
        '(0.676) but eighth of nine by mean rank, behind even the naive forecast. And the in-sample/out-of-sample '
        'inversion stands: SBA, the in-sample champion on Online '
        'Retail II, remains seventh or eighth of nine out-of-sample under either metric. Two MASE headlines, '
        'however, are '
        'exposed as properties of the metric rather than of the methods, and should be read as such. The '
        'naive benchmark, winner of the most MAE ties on the sparse tail, has the worst aggregate RMSSE on '
        'both panels (1.001 on M5, 0.800 on Online Retail II) and is worst in seven of the eight demand '
        'classes; only on Online Retail II’s lumpy class is it beaten downward, by Croston '
        'and SBA. The intermittent-demand specialists recover on the sparse panel, where SBA closes most of its '
        'gap to Naive (5.764 against 5.541, from 5.616 against 4.877 under MASE). On M5 the picture is '
        'mixed: Croston improves its mean rank from 5.205 to 4.890 while SBA slips from 5.211 to 5.579, and '
        'both were already ahead of the short moving average under MASE. This is broadly '
        'consistent with the long-standing argument that MAE-type scoring '
        'undervalues mean-rate estimators. Even the “unforecastable tail” softens: on M5’s intermittent and '
        'lumpy classes the smoothing, TSB, aggregation and machine-learning forecasters all attain RMSSE '
        'below 1 (LightGBM 0.875 and 0.762; TSB 0.915 and 0.799; SES 0.913 and 0.801) although every one of '
        'them exceeds MASE = 1. On the intermittent class the naive benchmark, Croston and SBA remain above '
        '1; on the lumpy class the metric change is enough to pull every method below it, the naive '
        'benchmark included, at 0.964. The eleven-method comparison on the '
        'neural-eligible subset sharpens it: under RMSSE LightGBM becomes significantly the '
        'best-ranked method on M5 (mean rank 3.65 against 4.76 for DeepAR; n = 29,486), which under MASE it '
        'was not, the top three being inseparable there (Section 5.10). While on Online '
        'Retail II the squared-error view pulls the deep models, tuned smoothing and temporal aggregation to '
        'parity. SES attains both the best mean RMSSE (0.560, with ADIDA and MAPA at 0.563 and NHITS at 0.570) '
        'and the best mean rank (5.08), with DeepAR seven thousandths behind at 5.09, while the naive forecast '
        'is worst by mean RMSSE and Croston worst by rank, the gradient-boosted model sitting just above '
        'Croston at the rear. The '
        'practical reading is that method selection must be conditioned on the demand '
        'regime and on the loss the business cares about: median-like service metrics favour simple '
        'zero-tolerant methods, while mean-cost metrics favour the rate estimators and the machine-learning models.'))
    A(('table', ['Method', 'M5 mean RMSSE', 'M5 rank', 'OR2 mean RMSSE', 'OR2 rank'],
        [['Naive', '1.001', '7.919', '0.800', '5.541'],
         ['SMA', '0.858', '6.170', '0.678', '4.346'],
         ['SES', '0.823', '4.420', '0.654', '4.180'],
         ['Croston', '0.900', '4.890', '0.759', '6.066'],
         ['SBA', '0.905', '5.579', '0.751', '5.764'],
         ['TSB', '0.826', '3.975', '0.665', '4.694'],
         ['ADIDA', '0.825', '4.525', '0.657', '4.227'],
         ['MAPA', '0.835', '4.462', '0.660', '4.379'],
         ['LightGBM (global)', '0.789', '3.060', '0.676', '5.804']],
        [1.5, 1.25, 1.0, 1.3, 1.0],
        'Table 8. RMSSE sensitivity, nine core methods on the full eligible sets (mean RMSSE and mean '
        'per-series RMSSE rank; lower is better). Critical distances at the 5% level: 0.069 (M5, '
        'n = 30,460) and 0.184 (OR2, n = 4,284). Under the mean-rewarding metric the naive benchmark is the '
        'weakest method on both datasets, while the substantive leaders are unchanged. TSB has the best '
        'per-series rank of any classical method on M5 under this metric (3.975).'))

    A(('h2', '5.9 Falsifying the data-sufficiency explanation with pretrained models'))
    A(('p', 'The explanation offered so far for the collapse of machine-learning accuracy on sparse demand is '
        'data sufficiency: each series carries too few events for a model to learn anything from it. That '
        'explanation makes a prediction, and the prediction is testable. A model pretrained on a large '
        'external corpus and applied zero-shot never fits the panel under study at all, so if the binding '
        'constraint were per-series history, such a model should not share the limitation. We therefore run '
        'Chronos-Bolt (Ansari et al., 2024) and TimesFM (Das et al., 2024) on both panels, zero-shot, scored '
        'on the same series under the same rolling-origin protocol as every other method.'))
    A(('p', 'The prediction is not borne out (Table 10). On M5 the best zero-shot model is beaten by the best '
        'trained model on the intermittent class (1.195 against 1.153) and on the lumpy class (1.078 against '
        '1.045). On Online Retail II the same ordering holds, by 0.017 and 0.016. The gap is positive in all '
        'four sparse cells, and a paired bootstrap over series (4,000 resamples) puts all four '
        'intervals clear of zero. Because the tier winner in '
        'each cell is the minimum of three candidates scored on the same test data, which biases the gap '
        'upward, we also repeated the comparison with the representatives fixed in advance (NHITS against '
        'Chronos-Bolt-Small). That specification gives gaps of +0.042, +0.033, +0.015 and '
        '+0.022. The bootstrap interval excludes zero in all four, but on Online Retail II’s intermittent class the normal interval does not (t = 1.83, -0.001 to +0.031), so that cell alone is not decisive under the pre-registered pairing. On every sparse class, then, removing the need to fit does not '
        'help. We note that in the previous version of this analysis, which classified series over the full '
        'span rather than the training window, the Online Retail II intermittent cell drew level rather than '
        'losing; the difference is traced in Section 5.4 and is a property of which series the class '
        'contained, not of the models.'))
    A(('p', 'The size of the gap is more informative than its sign. On the dense panel, per-series training '
        'is worth roughly 0.04 of mean MASE on the sparse classes; on the sparse panel it is worth 0.016 to '
        '0.017, a little under half as much. The value of fitting to the series in front of you falls as that '
        'series thins out, which is what the data-sufficiency argument predicts, but it falls towards zero '
        'rather than towards a deficit that pretraining can fill. What separates the strong methods from the '
        'weak ones on Online Retail II is the model class, not the fitting: NHITS, DeepAR and both '
        'Chronos-Bolt checkpoints all '
        'land between 0.685 and 0.706 on the intermittent class while tuned exponential smoothing sits at '
        '0.942 and the gradient-boosted model at 1.088, level with a naive random walk at 1.089.'))
    A(('p', 'The strongest evidence here is that the two zero-shot models agree with each other far more '
        'closely than either agrees with the trained models. Chronos-Bolt is a T5 encoder-decoder that chunks the '
        'context into patches and regresses quantiles directly; TimesFM is a patched decoder-only forecaster. '
        'Both are patch-based transformers, so they are not architecturally unrelated, but they were built by '
        'different groups and trained on different corpora, and Chronos-Bolt’s corpus composition is not '
        'published. Yet on M5 they land within 0.003 of one another in every demand '
        'class (0.812 against 0.815 on smooth, 0.743 against 0.745 on erratic, 1.195 against 1.197 on '
        'intermittent, 1.078 against 1.078 on lumpy) and report overall mean MASE of 0.961 and 0.964. Two '
        'independent routes to the same ceiling is what a limit in the data looks like, not a limit in any '
        'one model. It also makes the obvious objection less likely, that the result is a quirk of one pretraining '
        'corpus.'))
    A(('p', 'This also sharpens the reading of Section 5.4. Measured by mean MASE rather than by counting '
        'per-series wins, the sparse tail is not unforecastable. On Online Retail II the deep and pretrained '
        'models cut error on the intermittent class by 27% against the best simple method, and on the lumpy '
        'class by 14%. The earlier statement that nothing beats a naive benchmark there is a statement about '
        'Percentage-Best, which rewards forecasting zero on series that are mostly zero. Both readings are '
        'correct about their own metric, and Section 6 sets out which one a planner should act on.'))
    A(('table',
        ['Panel and demand class', 'Best simple', 'Best trained', 'Best zero-shot',
         'Zero-shot minus trained', '95% CI'],
        [['M5, Intermittent (n = 10,149)', 'SES 1.204', 'NHITS 1.153', 'Chronos-Bolt-S 1.195', '+0.042', '+0.032 to +0.057'],
         ['M5, Lumpy (n = 2,414)', 'SES 1.096', 'NHITS 1.045', 'Chronos-Bolt-S 1.078', '+0.033', '+0.026 to +0.040'],
         ['OR2, Intermittent (n = 494)', 'SES 0.942', 'DeepAR 0.685', 'Chronos-Bolt-B 0.703', '+0.017', '+0.006 to +0.031'],
         ['OR2, Lumpy (n = 2,355)', 'SES 0.723', 'NHITS 0.620', 'Chronos-Bolt-B 0.636', '+0.016', '+0.010 to +0.022']],
        [1.9, 1.0, 1.0, 1.25, 1.15, 1.35],
        'Table 10. The data-sufficiency test on the sparse demand classes, with paired 95% bootstrap intervals '
        'on the gap (4,000 resamples; results/gap_ci.json). Mean MASE for the best method in '
        'each tier, scored on the common subset (n = 29,486 M5 and 3,977 OR2). A positive final column means '
        'the zero-shot model is worse than the trained one. It is positive everywhere, so pretraining on an '
        'external corpus does not substitute for the per-series history the sparse tail lacks. The gap is '
        'roughly half as large on the sparse panel as on the dense one. Produced by '
        'code/26_foundation_analysis.py.'))

    A(('h2', '5.10 Statistical significance of the rankings'))
    A(('p', 'The orderings above are mostly, though not entirely, statistically decisive (Table 7, Figure 7). '
        'On the full M5 set '
        '(n = 30,460; critical distance 0.069) LightGBM’s mean MASE rank of 3.52 is significantly better '
        'than every other method, with TSB (4.26) a significantly separated second and SES (4.53) third. On '
        'the full Online Retail II set (n = 4,284; critical distance 0.184) the short moving average attains '
        'the best mean rank (3.98), with SES (4.21) and the two aggregation methods (4.23, 4.45) behind it; '
        'the leak-free LightGBM ranks eighth of nine (6.02), significantly worse than every simple method. '
        'On the neural-eligible subset with all eleven methods (Figure 7) the M5 result is a three-way tie '
        'rather than a win: LightGBM (4.45), DeepAR (4.51) and NHITS (4.52) are separated by less than the '
        '0.088 critical distance, so the dense-panel conclusion is that the three flexible global models are '
        'indistinguishable from one another and jointly ahead of everything simpler, not that gradient '
        'boosting wins. On Online '
        'Retail II DeepAR attains the best mean rank (3.72), significantly ahead of every other method. The '
        'rank view also exposes a useful '
        'distinction between consistency and magnitude: on Online Retail II NHITS achieves the lowest mean '
        'MASE (it wins big where it wins) while DeepAR is the most consistently accurate series-by-series; '
        'likewise SES leads SMA on mean MASE but trails it on mean rank. Both views agree on the substantive '
        'conclusions: machine-learning methods dominate the dense panel, simple and deep methods divide the sparse one, '
        'and the gradient-boosted model without leaked information is significantly behind simple smoothing '
        'there.'))
    A(('p', 'The intervals rest on an assumption the dense panel does not satisfy. The Nemenyi critical distance treats the N series as independent blocks. M5 is not N independent series: it is 3,049 products observed in ten stores each, and the same product in ten stores is closer to one observation than to ten. Repeating the test on product-level mean ranks, so that N is the number of distinct products rather than store-SKU pairs, widens the critical distance from 0.069 to 0.218 on the nine-method comparison and from 0.088 to 0.275 on the eleven-method one. Every conclusion we draw from it survives: the gradient-boosted model stays significantly ahead of all eight classical methods on M5 (its nearest classical rival, TSB, sits 0.734 of a rank behind), and the three flexible global models remain indistinguishable from one another at the top of the eleven-method comparison, which was already our reading at the narrower distance. What the clustered distance does remove is any claim to separate methods lying within about a fifth of a rank of each other, such as MAPA from Croston on M5, which the unclustered distance did separate. Online Retail II has a single seller and no store dimension, so its series are already products and the two distances coincide. We report the unclustered figures in Table 7 because the store-level series are genuinely distinct forecasting problems even when their demand is correlated, and the clustered figures here so that the independence assumption is checked and not simply asserted.'))
    A(('table', ['Method', 'M5 mean rank', 'OR2 mean rank'],
        [['Naive', '7.334', '4.877'],
         ['SMA', '5.718', '3.979'],
         ['SES', '4.532', '4.211'],
         ['Croston', '5.205', '6.542'],
         ['SBA', '5.211', '5.616'],
         ['TSB', '4.257', '5.075'],
         ['ADIDA', '4.572', '4.228'],
         ['MAPA', '4.648', '4.453'],
         ['LightGBM (global)', '3.523', '6.019']],
        [1.5, 1.4, 1.4],
        'Table 7. MCB analysis, nine core methods on the full eligible sets: mean per-series MASE ranks '
        '(lower is better). Critical distances at the 5% level: 0.069 (M5, n = 30,460) and 0.184 (OR2, '
        'n = 4,284); every pairwise gap larger than the critical distance is statistically significant. '
        'Figure 7 reports the eleven-method analysis on the neural-eligible subset.'))
    A(('figure', 'fig7_mcb.png',
        'Figure 7. MCB/Nemenyi mean-rank intervals on the neural-eligible subset (eleven methods). Intervals '
        'overlapping the best method’s are statistically indistinguishable from it at the 5% level.'))

    A(('h2', '5.11 Robustness across hold-out horizons'))
    A(('p', 'The substantive rankings are stable across hold-out horizons (Figure 6, Table 5; all cells use '
        'the same per-split eligibility as the primary analysis, so the primary-split rows match Table 3 '
        'exactly). At test windows of 13, 26 and 39 weeks on M5, LightGBM records the lowest mean MASE every '
        'time, SES is the best classical method, and Croston/SBA trail at the two longer horizons. On Online '
        'Retail II, tuned smoothing or its aggregated variants lead at every horizon, SES at 14 and 20 weeks and '
        'MAPA narrowly at 8 (0.812 against 0.814), and the leak-free LightGBM is close behind only at the '
        'primary 14-week window (0.868 against 0.835). At the other two splits it is beaten by every '
        'classical method except Croston and SBA, and at 8 weeks it is beaten by all of them. That cell '
        'exposes an operational fragility simple methods do not share: the six-week validation band there '
        'coincides with the retailer’s pre-Christmas demand surge, early stopping halts after 87 trees, '
        'and the underfit model emits small positive rates even for dormant items, errors that the '
        'scale-sensitive mean MASE amplifies to 1.104 while the median for the same cell stays at 0.591. '
        'The 20-week split fails in the same way but not for the same reason (1.026 against a median of 0.585, '
        '162 trees): its validation band falls in the June and July trough rather than the autumn ramp, so early stopping is misled by a band that is unrepresentatively quiet instead of unrepresentatively busy. That makes the point sharper than a single bad cell would, because the global model’s standing '
        'on this panel depends on where the validation band happens to fall and not on which direction it is atypical in, and a practitioner does not get '
        'to choose that. The qualitative conclusions of the out-of-sample comparison (the conditional machine-learning '
        'advantage, and the collapse of complex methods’ edge on sparse demand), are invariant to the split.'))
    A(('table', ['Hold-out', 'Naive', 'SMA', 'SES', 'Croston', 'SBA', 'TSB', 'MAPA', 'LightGBM'],
        [['M5 13 wk', '1.153', '1.004', '0.969', '1.084', '1.084', '0.972', '0.986', '0.939'],
         ['M5 26 wk', '1.140', '1.005', '0.974', '1.146', '1.138', '0.985', '0.996', '0.936'],
         ['M5 39 wk', '1.188', '1.058', '1.025', '1.295', '1.286', '1.038', '1.051', '0.975'],
         ['OR2 8 wk', '0.943', '0.857', '0.814', '1.079', '1.051', '0.815', '0.812', '1.104'],
         ['OR2 14 wk', '0.957', '0.866', '0.835', '1.115', '1.088', '0.847', '0.841', '0.868'],
         ['OR2 20 wk', '0.966', '0.881', '0.857', '1.137', '1.100', '0.879', '0.865', '1.026']],
        [1.2, 0.78, 0.78, 0.78, 0.88, 0.78, 0.78, 0.78, 0.95],
        'Table 5. Mean OOS MASE by hold-out horizon, computed under the same per-split eligibility filter as '
        'Table 3; the 26-week (M5) and 14-week (OR2) rows are the primary split and match Table 3 exactly. '
        'MAPA is carried as the representative temporal-aggregation method; ADIDA, whose two-parameter grid '
        'is refitted per split, is reported at the primary split only (Tables 2, 3 and 9). '
        'The OR2 8-week and 20-week LightGBM cells reflect a validation-band failure of early stopping during '
        'the pre-Christmas demand surge (87 and 162 trees; the medians for those cells are 0.591 and 0.585). '
        'See Section 5.11.'))

    A(('h2', '5.12 Beyond point accuracy: a distributional evaluation'))
    A(('p', 'Every ranking so far has been a point-forecast ranking, and Kolassa (2016) argues in this journal '
        'that point errors are the wrong object in low-count retail settings. His ground is stronger than the '
        'one we act on: what a planner needs is the entire discrete predictive distribution, scored with '
        'tools built for it, and measures such as MAD, MASE and wMAPE are inherently unsuitable for count '
        'data. We take a narrower step, scoring the service-relevant quantiles of that distribution rather '
        'than the distribution as a whole, on the practical ground that a stocking decision reads a quantile. '
        'Since the '
        'paper’s own thesis is that the metric must match the decision, we close by applying that test to '
        'ourselves. On Online Retail II, the sparse panel where the argument bites hardest, we score the two '
        'Chronos-Bolt checkpoints, which emit native predictive quantiles at no extra fitting cost, against a '
        'model-free benchmark, under the identical rolling-origin protocol and on the '
        'neural-eligible series (n = 4,094, the subset of Table 6 rather than the full eligible set of the '
        'other tables). DeepAR and NHITS also emit predictive distributions and extending the comparison to '
        'them is the obvious next step; we did not refit them here. We use pinball loss averaged over the quantile levels '
        '{0.5, 0.6, 0.7, 0.8, 0.9} and scaled per series by the same in-sample naive MAE that defines MASE, '
        'together with empirical coverage at the nominal 90th percentile. The benchmark is the per-series '
        'empirical quantile of the training window held constant across the test window, which is what a '
        'planner gets from the demand history alone and is strong on intermittent data because it reproduces '
        'the zeros.'))
    A(('p', 'The zero-shot models carry their point-accuracy advantage into the distribution. Chronos-Bolt-Base '
        'attains a scaled pinball loss of 0.376 and Chronos-Bolt-Small 0.381, against 0.476 for the empirical '
        'benchmark, a reduction of about 20% with no fitting to this dataset at all; all three are close to '
        'nominal at the 90th percentile (92.2%, 92.4% and 92.4%). On this evidence the earlier point-accuracy '
        'result is not an artefact of scoring the centre of the distribution.'))
    A(('p', 'What the models cannot do matters more here than what they can. Inventory policy is written at '
        'high service levels, commonly the 95th or 99th percentile, and the released Chronos-Bolt checkpoints '
        'are trained on the deciles 0.1 to 0.9. Asking for a higher quantile does not raise. It returns the 0.9 '
        'value, clamped: across a sample of 256 series, and for both released checkpoints, the requested '
        '95th and 99th percentiles came back identical to the 90th for 100% of series. TimesFM-1.0 has the '
        'same ceiling, which is why it is absent from this comparison; we checked rather than assumed it, '
        'and the loaded checkpoint declares the grid 0.1 to 0.9 and returns ten columns per series, a mean '
        'and those nine deciles, with nothing above the 90th to read. This limitation is documented, and the '
        'chronos-forecasting library logs a warning naming the trained range whenever a level outside it is '
        'requested, so it is not hidden. It is, however, easy to lose: the message is emitted through the '
        'logging system rather than as a Python warning or an exception, so it is not caught by warning '
        'filters, does not interrupt a batch job, and does not change the shape of the returned array. A '
        'pipeline that does not read its logs receives a 90th percentile labelled as a 99th. The contrast '
        'with Section 5.7 is instructive rather than parallel: the price leak carried no warning of any kind, '
        'whereas here the tool says what it is doing and the reader has to be listening. The empirical '
        'benchmark expresses any quantile the '
        'training window supports. Extending this evaluation to M5 and to the trained neural models, which '
        'emit full predictive distributions, is the natural next step; we report the sparse panel here '
        'because that is where the distributional argument is strongest and where the tail limitation '
        'matters most.'))
    A(('table', ['Method (Online Retail II, n = 4,094)', 'Scaled pinball', 'Coverage at nominal 90%',
                 'Highest expressible quantile'],
        [['Empirical training quantile', '0.476', '92.4%', 'any'],
         ['Chronos-Bolt-Small (zero-shot)', '0.381', '92.4%', '0.90'],
         ['Chronos-Bolt-Base (zero-shot)', '0.376', '92.2%', '0.90']],
        [2.3, 1.1, 1.5, 1.5],
        'Table 12. Distributional evaluation on the sparse panel: pinball loss averaged over the levels '
        '{0.5, 0.6, 0.7, 0.8, 0.9} and scaled per series by the in-sample naive MAE, plus empirical coverage '
        'at the nominal 90th percentile. Scored under the same rolling-origin protocol as every other table, on the '
        'neural-eligible subset of Table 6 (n = 4,094) and not on the wider eligible set of Tables 3 and 4. '
        'The final column is the point of the section: the two Chronos-Bolt '
        'checkpoints are trained on deciles, so a request for the 95th or 99th percentile returns the 90th '
        'unchanged. Produced by code/28_probabilistic.py.'))

    A(('h2', '5.13 Design demonstration IV: the tuning grid'))
    A(('p', 'A fourth design choice is the range over which the classical methods are tuned. Our smoothing constants follow the range used in the intermittent-demand literature, where Croston (1972) recommends low values and the comparative studies of Syntetos and Boylan (2005) and Teunter and Duncan (2009) work in roughly [0.01, 0.3], with level smoothing no higher than 0.4. Within that range the per-series tuner selects an endpoint on 54% to 89% of series depending on method and panel, and an endpoint selection is the signature of a search that wanted to go further. Read on its own it says the classical arm is under-tuned, which in a comparison against machine learning would be a serious objection: a weak baseline manufactures the result. So we tested it, re-running the six singly-tuned classical methods on grids extended at both ends, down to 0.005 for the level methods and 0.0005 for the Croston family and up to 0.9 and 0.95 respectively. Pushing further still moves Croston by 0.002 and SBA by 0.003, so for the Croston family the grid has stopped binding. MAPA is the exception and keeps degrading, by a further 0.026, which is the same effect this section is about rather than a sign that its grid is too narrow. ADIDA is tuned over a two-parameter grid and is left out of this sweep.'))
    A(('p', 'The objection does not survive the test, and the way it fails is informative. On M5 the grid barely matters: every method moves by less than 0.01 of mean MASE, in both directions. On Online Retail II the wider grid makes the level-based methods substantially worse, by 0.034 for SES, 0.032 for TSB and 0.043 for MAPA, while improving the Croston family, by 0.068 for SBA and 0.034 for Croston. The narrow range regularised exponential smoothing instead of handicapping it. Given the freedom, 27.6% of Online Retail II series select an SES smoothing constant above 0.4, and those series average 26.3 active weeks of training history against 41.9 for the rest: they are the short, sparse ones, whose training-window criterion is noisy enough that the extra freedom is spent fitting noise instead of demand. On M5, where 26.4% of series make the same choice but from histories of 138.7 active weeks against 153.2, the effect nearly vanishes. The literature range is doing the work of a shrinkage prior, and it matters most on the panel where the histories are shortest.'))
    A(('p', 'This is the fourth time in the paper that a choice about the evaluation, and not about the methods, has moved the answer. It is also the hardest of the four to notice. A horizon, a feature and a metric all leave a mark on a results table; a tuning grid is a line of configuration that none of them displays. Its effect, like the horizon effect of Section 5.6, is itself regime-conditional, negligible where histories are long and material where they are short, which is the boundary the rest of the paper draws. We keep the literature grids for every headline result and report the wide-grid figures alongside them (code/36_grid_sensitivity.py) so that the choice is visible and not assumed.'))
    A(('h1', '6. Discussion'))
    A(('h2', '6.1 Guidance for method selection'))
    A(('p', 'Table 11 collapses the results into the choice a planner actually faces: given a demand class '
        'and a panel like this one, which method should run in production. Two columns are reported rather '
        'than one because on this data mean MASE and Percentage-Best disagree in six of the eight cells, and '
        'a planner who reads only one of them will pick the wrong method in three cells out of four. Mean MASE rewards '
        'estimating the demand rate, which is what an inventory calculation consumes. Percentage-Best counts '
        'outright wins per series, which on mostly-zero demand rewards forecasting zero. Neither is wrong; '
        'they answer different questions.'))
    A(('p', 'The rule that falls out is short. Where demand is dense, the global gradient-boosted model is '
        'the best single choice by either metric, and the margin over tuned exponential smoothing is real but '
        'moderate at 3.3 to 5.2% by class for the gradient-boosted model itself and 3.9% overall. Where demand is sparse and each series still carries enough history to be '
        'modelled, the deep and pretrained models are worth the engineering: they cut mean error by 14 to 27% '
        'against the best simple method, which is the largest accuracy gain anywhere in this study. Where '
        'demand is sparse and the decision is driven by how often a forecast is exactly right rather than by '
        'total error, simple zero-tolerant methods remain hard to beat and cost nothing to run. The choice '
        'between the last two is a choice about the loss function, and it should be made deliberately rather '
        'than inherited from whatever the planning system reports by default.'))
    A(('table',
        ['Panel and class', 'n', 'Lowest mean MASE', 'Gain over best simple', 'Most series won', 'Guidance'],
        [['M5, Smooth', '15,125', 'LightGBM 0.788', '4.4%', 'LightGBM (global) 39.8%', 'Global ML model'],
         ['M5, Erratic', '1,798', 'LightGBM 0.727', '5.2%', 'LightGBM (global) 39.9%', 'Global ML model'],
         ['M5, Intermittent', '10,149', 'NHITS 1.153', '4.2%', 'LightGBM (global) 31.1%', 'ML, but no method beats MASE 1'],
         ['M5, Lumpy', '2,414', 'NHITS 1.045', '4.7%', 'LightGBM (global) 32.8%', 'ML, but no method beats MASE 1'],
         ['OR2, Smooth', '94', 'DeepAR 0.835', '9.1%', 'SMA 24.0%', 'Deep model; the class is small'],
         ['OR2, Erratic', '1,034', 'Chronos-Bolt-Small 0.697', '6.6%', 'SBA 20.2%', 'Deep or pretrained model'],
         ['OR2, Intermittent', '494', 'DeepAR 0.685', '27.3%', 'Naive 25.6%', 'Deep model if scoring mean error'],
         ['OR2, Lumpy', '2,355', 'NHITS 0.620', '14.2%', 'Naive 27.5%', 'Deep model if scoring mean error']],
        [1.35, 0.6, 1.45, 0.95, 1.1, 1.75],
        'Table 11. Method selection by demand class and panel. "Gain over best simple" is the reduction in '
        'mean MASE against the best of Naive, SMA and SES. The two metric columns disagree in six of eight '
        'cells. Mean MASE favours the more complex model in all six, while Percentage-Best '
        'favours a different one. Which method that is depends on the panel: on M5 the win count is taken by the '
        'gradient-boosted model in all four classes, so the disagreement there is between a mean computed '
        'over fourteen methods and a win count computed over the nine core ones; on Online Retail II it is '
        'taken by a zero-forecasting simple method in three classes of four. Match the metric to the '
        'decision before reading the guidance column. '
        'Produced by code/27_managerial_table.py.'))

    A(('p', 'Two messages follow for supply-chain demand planning. The first concerns governance of the '
        'forecasting process: method selection must be done out-of-sample. Because planning systems routinely '
        'surface in-sample fit as the basis for choosing a method, and because that statistic inverts the true '
        'out-of-sample ranking (crowning, on one of our datasets, exactly the method a naïve forecast beats), '
        'organisations may be committing inventory capital on the strength of a number that points the wrong '
        'way. Rolling-origin validation with scale-free metrics is inexpensive and should be standard. The '
        'same governance must extend to features: our same-week transacted-price variable, an easy default on '
        'transactional data, perfectly identified sale weeks and silently inflated the machine-learning model’s measured '
        'accuracy by 0.190 of mean MASE on the sparse dataset, from 0.868 to 0.678 (Section 5.7). Evaluating models '
        'out-of-sample is not sufficient if the features themselves look across the forecast origin. Nor is '
        'a single error metric sufficient: median-rewarding measures flatter zero-forecasters and '
        'mean-rewarding measures flatter the rate estimators and machine-learning models (Section 5.8), so the metric must '
        'be matched to the decision the forecast feeds.'))
    A(('p', 'The second message concerns where, and in what form, to invest in machine learning. Our results support a '
        'regime-conditional posture rather than blanket adoption or blanket scepticism. On the dense, '
        'higher-volume, feature-rich part of an assortment, the items that also carry most of the revenue and '
        'inventory value, the global gradient-boosted model delivers a real, if moderate, accuracy gain and is '
        'worth the engineering investment. On sparse catalogues the value of cross-learning survives only in '
        'the deep global models, and only for series long enough to train on; the gradient-boosted model, '
        'stripped of leaked information, does not beat disciplined exponential smoothing there. For the long '
        'sparse tail of intermittent and lumpy items, which numerically dominates most catalogues and which '
        'from which roughly three to four percent of series are excluded for want of history, no method wins a '
        'majority of series outright against '
        'a naive benchmark, although on the sparse panel the deep and pretrained models still cut mean '
        'error substantially. Which of those two readings should drive a decision depends on the loss the '
        'business actually carries. The productive response there is as much an inventory-policy one as a '
        'forecasting one, sizing safety stock against service-level targets, criticality and lead-time '
        'risk. Matching forecasting sophistication to demand regime, data sufficiency and the decision '
        'metric is the efficient frontier. This conditional view both validates the industry turn to machine learning and guards against '
        'over-claiming for it, a distinction that matters as these systems mediate critical '
        'infrastructure and food supply.'))
    A(('p', 'Several limitations bound the conclusions. Both datasets are retail and weekly; other sectors '
        '(industrial spares, pharmaceuticals) and finer granularities may differ. The MCB analysis of '
        'Section 5.10 separates most of the rank orderings, though not the three flexible global models on M5, '
        'which are inseparable there, and is reported both on the raw '
        'series and on product-level clusters because M5’s store-SKU series are not independent; '
        'per-series Diebold–Mariano panels '
        'remain a worthwhile extension. The distributional evaluation of Section 5.12 covers the sparse panel '
        'and the methods that emit predictive quantiles; extending it to M5 and to the trained neural models '
        'is left to future work. The Online '
        'Retail II panel excludes cancellations and returns, so demand on that dataset reflects gross '
        'orders; and each series enters at its first observed sale, so systematically delisted items are '
        'represented only up to the panel’s end. Our evaluation is '
        'error-based, whereas the operational cost of error is asymmetric and item-specific; a full cost- or '
        'service-level simulation is the natural next step beyond the quantile scoring of Section 5.12. We '
        'benchmark strong, representative '
        'classical, gradient-boosted, deep and pretrained forecasters, including the obsolescence-aware TSB '
        'estimator and both standard temporal-aggregation methods; hierarchical reconciliation remains a '
        'worthwhile extension. We expect the central regime-conditional finding (diminishing '
        'returns to model complexity as demand sparsifies) to be robust '
        'to these choices, but testing it further is valuable future work.'))

    A(('h1', '7. Conclusion'))
    A(('p', 'On two openly available retail datasets that bracket the demand spectrum, holding the data, the '
        'forecasters and the protocol fixed, we varied three individually defensible design choices. Each one '
        'reversed the ranking. Lengthening the horizon from one step to a replenishment lead time moved '
        'Croston from last of eight classical methods to fifth at a quarterly lead time and first at 26 weeks on '
        'the denser panel, the last of those resting on a single fully observed block per series. Restricting a single '
        'price feature to strictly past values moved the gradient-boosted model from ahead of every classical '
        'method to behind tuned exponential smoothing. Replacing MASE with RMSSE moved the naive benchmark '
        'from winning more series than any method but one on the sparse panel to the worst mean RMSSE on '
        'both. The in-sample '
        'statistic that planning systems use to '
        'select a method is a fourth such choice: it inverts the out-of-sample ordering on the sparse panel, and '
        'on the dense one costs the in-sample champion, ADIDA, two thirds of its win-rate and hands the '
        'lowest mean MASE to SES, the method ADIDA had narrowly beaten on the fitting window.'))
    A(('p', 'None of this makes the underlying comparison meaningless, and it is not an argument against '
        'machine learning. The regime-conditional reading survives all four variations, provided it is stated at '
        'the level of the model class rather than of machine learning as a whole: cross-sectional gradient '
        'boosting pays '
        'where demand is dense and history is long, and its advantage narrows or disappears on the sparse '
        'intermittent tail, where it finishes behind five classical methods. The deep global models are the '
        'exception and post their largest margins there, 27% over the best simple method on the sparse '
        'intermittent class against 3 to 5% per class on the dense panel, but only on the series long enough '
        'to admit them, which is the same data-sufficiency boundary read from the other side. It also '
        'survives a direct falsification test, since two pretrained models needing '
        'no per-series history do not beat trained models in any sparse demand class. What changes is what '
        'a ranking can be taken to mean. A leaderboard position is a joint property of a method and an '
        'evaluation, and reporting one without the other reports half the result.'))
    A(('p', 'The prescription for demand planning is correspondingly narrow. Match the error metric to the '
        'loss the decision carries, and the evaluation horizon to the replenishment cycle. Audit the timing of '
        'every feature before believing a gain, and check that a model can express the service quantile you '
        'intend to read from it. Validate out-of-sample, not on the fitting window. The sparse tail is then an '
        'inventory-policy problem rather than a reason to reach for a more complex model. Because the data are '
        'public and every step of the pipeline is specified, each design choice varied here can be varied '
        'again by others.'))

    _release = ('will be released publicly upon publication (and is available to reviewers in anonymized '
                'form during review)' if anonymous else
                'is available at https://github.com/NISHCHAY026/ai-demand-planning-benchmark')
    A(('h1', '8. Data availability and reproducibility'))
    A(('p', 'Both datasets are public: the M5 competition data (Walmart store–SKU sales, calendar and prices) '
        'and the UCI Online Retail II dataset (UCI Machine Learning Repository, ID 502). The complete '
        'pipeline (weekly panel construction, SBC classification, the eight classical forecasters, the global '
        'LightGBM model, the NHITS and DeepAR neural models, the rolling-origin evaluation, robustness sweeps, '
        'the horizon and metric sensitivities of Sections 5.6 and 5.8, and all figures) ' + _release + '. No proprietary data or software is '
        'required; results in all tables and figures regenerate end-to-end from the public sources. Two '
        'checks guard that claim. A consistency harness re-reads every numeric cell of Tables 1 to 12 and '
        'the quantitative claims made in the text, and compares each against the result file that '
        'produced it, failing on any disagreement beyond rounding; it currently runs several hundred such '
        'checks, and the exact count is printed by the harness itself. A '
        'provenance manifest records, for each result file, a hash of the source of exactly the library '
        'functions its producing script calls, so that a stale artefact is detected by changed code '
        'rather than guessed at from a modification time. The discarded Online Retail II price '
        'specification of Section 5.7 is retained behind an explicit flag and writes to separate files, '
        'so the leak counterfactual can be regenerated without any risk of it re-entering a headline '
        'result.'))

    A(('h1', 'Declaration of generative AI and AI-assisted technologies in the manuscript preparation process'))
    A(('p', 'During the preparation of this work the author used Claude (Anthropic) in order to help compile the manuscript. After using this tool, the author reviewed and edited the content as needed and takes full responsibility for the content of the published article.'))

    A(('h1', 'References'))
    A(('refs', [
        'Ansari, A.F., Stella, L., Turkmen, C., Zhang, X., Mercado, P., Shen, H., et al., 2024. Chronos: '
        'learning the language of time series. arXiv:2403.07815',
        'Bacchetti, A., Saccani, N., 2012. Spare parts classification and demand forecasting for stock '
        'control: investigating the gap between research and practice. Omega 40(6), 722–737.',
        'Babai, M.Z., Syntetos, A.A., Teunter, R., 2014. Intermittent demand forecasting: an empirical study '
        'on accuracy and the risk of obsolescence. International Journal of Production Economics 157, 212–219.',
        'Bojer, C.S., Meldgaard, J.P., 2021. Kaggle forecasting competitions: an overlooked learning '
        'opportunity. International Journal of Forecasting 37(2), 587–603.',
        'Challu, C., Olivares, K.G., Oreshkin, B.N., Garza, F., Mergenthaler-Canseco, M., Dubrawski, A., 2023. '
        'NHITS: neural hierarchical interpolation for time series forecasting. Proceedings of the AAAI '
        'Conference on Artificial Intelligence 37(6), 6989–6997.',
        'Chen, T., Guestrin, C., 2016. XGBoost: a scalable tree boosting system. Proceedings of the 22nd ACM '
        'SIGKDD International Conference on Knowledge Discovery and Data Mining, 785–794.',
        'Croston, J.D., 1972. Forecasting and stock control for intermittent demands. Operational Research '
        'Quarterly 23(3), 289–303.',
        'Das, A., Kong, W., Sen, R., Zhou, Y., 2024. A decoder-only foundation model for time-series '
        'forecasting. arXiv:2310.10688',
        'Friedman, J.H., 2001. Greedy function approximation: a gradient boosting machine. Annals of '
        'Statistics 29(5), 1189–1232.',
        'Garza, A., Challu, C., Mergenthaler-Canseco, M., 2023. TimeGPT-1. arXiv:2310.03589',
        'Giannopoulos, P.G., Dasaklis, T.K., Tsantilis, I., Patsakis, C., 2025. Machine learning algorithms in '
        'intermittent demand forecasting: a review. International Journal of Production Research, 1–43.',
        'Goswami, M., Szafer, K., Choudhry, A., Cai, Y., Li, S., Dubrawski, A., 2024. MOMENT: a family of '
        'open time-series foundation models. International Conference on Machine Learning. '
        'arXiv:2402.03885',
        'Hewamalage, H., Bergmeir, C., Bandara, K., 2021. Recurrent neural networks for time series '
        'forecasting: current status and future directions. International Journal of Forecasting 37(1), '
        '388–427.',
        'Hyndman, R.J., Koehler, A.B., 2006. Another look at measures of forecast accuracy. International '
        'Journal of Forecasting 22(4), 679–688.',
        'Januschowski, T., Gasthaus, J., Wang, Y., Salinas, D., Flunkert, V., Bohlke-Schneider, M., Callot, '
        'L., 2020. Criteria for classifying forecasting methods. International Journal of Forecasting 36(1), '
        '167–177.',
        'Kapoor, S., Narayanan, A., 2023. Leakage and the reproducibility crisis in machine-learning-based '
        'science. Patterns 4(9), 100804.',
        'Kaufman, S., Rosset, S., Perlich, C., Stitelman, O., 2012. Leakage in data mining: formulation, '
        'detection, and avoidance. ACM Transactions on Knowledge Discovery from Data 6(4), 1–21.',
        'Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., Liu, T.-Y., 2017. LightGBM: a '
        'highly efficient gradient boosting decision tree. Advances in Neural Information Processing Systems '
        '30, 3146–3154.',
        'Kolassa, S., 2016. Evaluating predictive count data distributions in retail sales forecasting. '
        'International Journal of Forecasting 32(3), 788–803.',
        'Koning, A.J., Franses, P.H., Hibon, M., Stekler, H.O., 2005. The M3 competition: statistical tests '
        'of the results. International Journal of Forecasting 21(3), 397–409.',
        'Kourentzes, N., 2013. Intermittent demand forecasts with neural networks. International Journal of '
        'Production Economics 143(1), 198–206.',
        'Kourentzes, N., 2014. On intermittent demand model optimisation and selection. International Journal '
        'of Production Economics 156, 180–190.',
        'Kourentzes, N., Petropoulos, F., Trapero, J.R., 2014. Improving forecasting by estimating time series '
        'structural components across multiple frequencies. International Journal of Forecasting 30(2), '
        '291–302.',
        'Lim, B., Arık, S.Ö., Loeff, N., Pfister, T., 2021. Temporal fusion transformers for interpretable '
        'multi-horizon time series forecasting. International Journal of Forecasting 37(4), 1748–1764.',
        'Makridakis, S., Spiliotis, E., Assimakopoulos, V., 2020. The M4 competition: 100,000 time series and '
        '61 forecasting methods. International Journal of Forecasting 36(1), 54–74.',
        'Makridakis, S., Spiliotis, E., Assimakopoulos, V., 2022. M5 accuracy competition: results, findings, '
        'and conclusions. International Journal of Forecasting 38(4), 1346–1364.',
        'Montero-Manso, P., Hyndman, R.J., 2021. Principles and algorithms for forecasting groups of time '
        'series: locality and globality. International Journal of Forecasting 37(4), 1632–1653.',
        'Nikolopoulos, K., Syntetos, A.A., Boylan, J.E., Petropoulos, F., Assimakopoulos, V., 2011. An '
        'aggregate–disaggregate intermittent demand approach (ADIDA) to forecasting: an empirical proposition '
        'and analysis. Journal of the Operational Research Society 62(3), 544–554.',
        'Oreshkin, B.N., Carpov, D., Chapados, N., Bengio, Y., 2020. N-BEATS: neural basis expansion analysis '
        'for interpretable time series forecasting. International Conference on Learning Representations.',
        "Petropoulos, F., Makridakis, S., Assimakopoulos, V., Nikolopoulos, K., 2014. 'Horses for courses' in "
        'demand forecasting. European Journal of Operational Research 237(1), 152–163.',
        'Petropoulos, F., et al., 2022. Forecasting: theory and practice. International Journal of Forecasting '
        '38(3), 705–871.',
        'Petropoulos, F., Kourentzes, N., 2015. Forecast combinations for intermittent demand. Journal of the '
        'Operational Research Society 66(6), 914–924.',
        'Pinçe, Ç., Turrini, L., Meissner, J., 2021. Intermittent demand forecasting for spare parts: a '
        'critical review. Omega 105, 102513.',
        'Rasul, K., Ashok, A., Williams, A.R., Ghonia, H., Bhagwatkar, R., Khorasani, A., et al., 2023. '
        'Lag-Llama: towards foundation models for probabilistic time series forecasting. arXiv:2310.08278',
        'Salinas, D., Flunkert, V., Gasthaus, J., Januschowski, T., 2020. DeepAR: probabilistic forecasting '
        'with autoregressive recurrent networks. International Journal of Forecasting 36(3), 1181–1191.',
        'Smyl, S., 2020. A hybrid method of exponential smoothing and recurrent neural networks for time '
        'series forecasting. International Journal of Forecasting 36(1), 75–85.',
        'Syntetos, A.A., Babai, M.Z., Boylan, J.E., Kolassa, S., Nikolopoulos, K., 2016. Supply chain '
        'forecasting: theory, practice, their gap and the future. European Journal of Operational Research '
        '252(1), 1–26.',
        'Syntetos, A.A., Boylan, J.E., 2001. On the bias of intermittent demand estimates. International '
        'Journal of Production Economics 71(1–3), 457–466.',
        'Syntetos, A.A., Boylan, J.E., 2005. The accuracy of intermittent demand estimates. International '
        'Journal of Forecasting 21(2), 303–314.',
        'Syntetos, A.A., Boylan, J.E., Croston, J.D., 2005. On the categorization of demand patterns. Journal '
        'of the Operational Research Society 56(5), 495–503.',
        'Tashman, L.J., 2000. Out-of-sample tests of forecasting accuracy: an analysis and review. '
        'International Journal of Forecasting 16(4), 437–450.',
        'Teunter, R.H., Duncan, L., 2009. Forecasting intermittent demand: a comparative study. Journal of the '
        'Operational Research Society 60(3), 321–329.',
        'Teunter, R.H., Syntetos, A.A., Babai, M.Z., 2011. Intermittent demand: linking forecasting to '
        'inventory obsolescence. European Journal of Operational Research 214(3), 606–615.',
        'U.S. Census Bureau, 2026. Manufacturing and Trade Inventories and Sales: total business '
        'inventories, seasonally adjusted (series BUSINV), June 2026. '
        'https://www.census.gov/econ/currentdata/',
        'U.S. Executive Order 14017, 2021. America’s Supply Chains. Federal Register 86, 11849–11854 '
        '(March 1, 2021).',
        'Wallström, P., Segerstedt, A., 2010. Evaluation of forecasting error measurements and techniques for '
        'intermittent demand. International Journal of Production Economics 128(2), 625–636.',
        'Willemain, T.R., Smart, C.N., Schwarz, H.F., 2004. A new approach to forecasting intermittent demand '
        'for service parts inventories. International Journal of Forecasting 20(3), 375–387.',
        'Woo, G., Liu, C., Kumar, A., Xiong, C., Savarese, S., Sahoo, D., 2024. Unified training of '
        'universal time series forecasting transformers. arXiv:2402.02592',
        'Zhang, G.P., Xia, Y., Xie, M., 2024. Intermittent demand forecasting with transformer neural '
        'networks. Annals of Operations Research 339(1), 1051–1072.',
    ]))
    for _i, _blk in enumerate(B):
        if _blk[0] == 'refs':
            B[_i] = ('refs', _add_dois(_blk[1]))
    return B


def companion_blocks():
    """A companion document rendered alongside the paper by the same builders.

    Its content is personal to the author and lives in a separate, unpublished module,
    so a public clone of this repository does not have it. Returns (blocks, filename
    stem, is_brief); blocks is empty when the module is absent and the builders then
    render the paper only.
    """
    try:
        import niw_content as _c
    except ImportError:
        return [], None, False
    return _c.niw_blocks(), _c.OUTPUT_STEM, _c.IS_BRIEF


def titlepage_blocks():
    """Separate title page for double-blind submission (author identity lives here, not in
    the anonymized manuscript). Reuses the abstract and keywords from blocks()."""
    mb = blocks()
    abstract = next(mb[i + 1][1] for i, b in enumerate(mb) if b[0] == 'h_abstract')
    keywords = next(b[1] for b in mb if b[0] == 'keywords')
    B = [('title', TITLE),
         ('authors', AUTHORS, AFFIL),
         ('note', 'Corresponding author: Nishchay Patel, Independent Researcher. '
                  'E-mail: [insert corresponding-author e-mail].'),
         ('h_abstract', 'Abstract'), ('p', abstract), ('keywords', keywords),
         ('h2', 'Declarations'),
         ('p', 'Funding: This research received no specific grant from any funding agency in the public, '
               'commercial or not-for-profit sectors.'),
         ('p', 'Declaration of competing interest: The author declares no competing interests.'),
         ('p', 'Data availability: Both datasets are publicly available: the M5 competition data and the '
               'UCI Online Retail II dataset (UCI Machine Learning Repository, ID 502). The complete analysis '
               'code will be released publicly upon publication.'),
         ('p', 'Declaration of generative AI and AI-assisted technologies in the manuscript preparation '
               'process: during the preparation of this work the author used Claude (Anthropic) in order '
               'to help compile the manuscript. After using this tool, the author reviewed and edited the '
               'content as needed and takes full responsibility for the content of the published article.'),
         ('p', 'Author contributions: Nishchay Patel is the sole author and is responsible for all aspects '
               'of the study.'),
         ('p', 'Prepared for submission to the International Journal of Forecasting (double-blind review). '
               'The accompanying manuscript file is anonymized; this title page carries the author '
               'identification.')]
    return B
