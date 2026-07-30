"""
07_figures.py -- publication figures for the cross-dataset study.
Saves PNGs (300 dpi) into results/figures/.
"""
import os, json, numpy as np, pandas as pd
import matplotlib as mpl; mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import lib

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
RES  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
FIG  = fr'{RES}\figures'; os.makedirs(FIG, exist_ok=True)

mpl.rcParams.update({'font.family':'serif','font.size':10,'axes.titlesize':11,
    'axes.labelsize':10,'axes.edgecolor':'#444','axes.linewidth':0.8,
    'figure.dpi':120,'savefig.dpi':300,'savefig.bbox':'tight'})
NAVY='#1E2761'; GOLD='#C9A227'
MCOL={'Naive':'#9AA0A6','SMA':'#7FB3D5','SES':'#16A085','Croston':'#E59866','SBA':'#C0392B','LightGBM (AI)':NAVY}
ORDER=['Naive','SMA','SES','Croston','SBA','LightGBM (AI)']
DSNAME={'m5':'M5 (Walmart, weekly)','or2':'Online Retail II (weekly)'}

def load_results(ds):
    c=pd.read_parquet(fr'{RES}\{ds}_classical.parquet')
    l=pd.read_parquet(fr'{RES}\{ds}_lgbm.parquet')
    df=c.merge(l,on='unique_id',how='left')
    df=df[np.isfinite(df['scale'])&(df['scale']>0)&(df['train_nnz']>=2)].copy()
    return df

# ============================ FIGURE 1: demand fingerprint ============================
fig,axes=plt.subplots(2,2,figsize=(10,7.2))
for j,ds in enumerate(['m5','or2']):
    cls=pd.read_parquet(fr'{DATA}\{ds}_classification.parquet')
    cc=cls[(cls['n_nonzero']>=2)&np.isfinite(cls['ADI'])].copy()
    cc['CV2c']=cc['CV2'].clip(1e-3,30); cc['ADIc']=cc['ADI'].clip(1,60)
    ax=axes[0,j]
    hb=ax.hexbin(cc['ADIc'],cc['CV2c'],gridsize=40,xscale='log',yscale='log',
                 cmap='BuPu',mincnt=1,bins='log')
    ax.axvline(1.32,color=NAVY,lw=1,ls='--'); ax.axhline(0.49,color=NAVY,lw=1,ls='--')
    ax.set_xlabel('ADI (avg inter-demand interval)'); ax.set_ylabel('CV² of non-zero sizes')
    ax.set_title(f'{DSNAME[ds]}\ndemand pattern density',fontsize=10)
    ax.text(0.97,0.04,'Intermittent',transform=ax.transAxes,ha='right',va='bottom',fontsize=8,color=NAVY)
    ax.text(0.03,0.96,'Erratic',transform=ax.transAxes,ha='left',va='top',fontsize=8,color=NAVY)
    ax.text(0.97,0.96,'Lumpy',transform=ax.transAxes,ha='right',va='top',fontsize=8,color='#C0392B')
    ax.text(0.03,0.04,'Smooth',transform=ax.transAxes,ha='left',va='bottom',fontsize=8,color='#16A085')
    # class shares
    axb=axes[1,j]
    dist=cc['class'].value_counts(normalize=True).reindex(['Smooth','Intermittent','Erratic','Lumpy']).fillna(0)*100
    bars=axb.bar(range(4),dist.values,color=['#16A085','#7FB3D5','#E59866','#C0392B'],edgecolor='k',lw=.5)
    axb.set_xticks(range(4)); axb.set_xticklabels(['Smooth','Intermit.','Erratic','Lumpy'],fontsize=9)
    axb.set_ylabel('% of classifiable series'); axb.set_ylim(0,70)
    for b,v in zip(bars,dist.values): axb.text(b.get_x()+b.get_width()/2,v+1,f'{v:.0f}%',ha='center',fontsize=8)
    axb.set_title(f'{DSNAME[ds]}: SBC class mix',fontsize=10)
fig.suptitle('Figure 1.  Demand fingerprints: a dense, partly smooth grocery panel (M5) versus a sparse, '
             'predominantly lumpy e-commerce panel (Online Retail II).',fontsize=10,y=1.005)
fig.tight_layout(); fig.savefig(fr'{FIG}\fig1_fingerprint.png'); plt.close(fig)
print('fig1 done')

# ============================ FIGURE 2: in-sample / OOS inversion ============================
fig,axes=plt.subplots(1,2,figsize=(10,4.2))
CLS=['Naive','SMA','SES','Croston','SBA']
for j,ds in enumerate(['m5','or2']):
    inv=pd.read_csv(fr'{RES}\{ds}_inversion.csv')
    inv=inv.set_index('method').reindex(CLS)
    x=np.arange(len(CLS)); w=0.38
    ax=axes[j]
    b1=ax.bar(x-w/2,inv['insample_PB_pct'],w,label='In-sample (training fit)',color='#B0BEC5',edgecolor='k',lw=.5)
    b2=ax.bar(x+w/2,inv['oos_PB_pct'],w,label='Out-of-sample (rolling origin)',color=NAVY,edgecolor='k',lw=.5)
    ax.set_xticks(x); ax.set_xticklabels(CLS,fontsize=9)
    ax.set_ylabel('Percentage-Best (% of series)'); ax.set_title(DSNAME[ds],fontsize=10)
    ax.legend(fontsize=8,frameon=False)
    # annotate the collapse of each panel's IN-SAMPLE champion
    champ=inv['insample_PB_pct'].idxmax(); xi=CLS.index(champ)
    ci=inv.loc[champ,'insample_PB_pct']; co=inv.loc[champ,'oos_PB_pct']
    ax.annotate('',xy=(xi+w/2,co+1.5),xytext=(xi-w/2,ci+1.5),
                arrowprops=dict(arrowstyle='->',color='#C0392B',lw=1.6))
    ax.text(xi,ci+3.5,f'{champ}\n{ci:.0f}%→{co:.0f}%',ha='center',color='#C0392B',fontsize=8.5,fontweight='bold')
fig.suptitle('Figure 2.  The in-sample → out-of-sample inversion. Methods that look best when scored on the '
             'history used to fit them are not those that generalise.',fontsize=10,y=1.02)
fig.tight_layout(); fig.savefig(fr'{FIG}\fig2_inversion.png'); plt.close(fig)
print('fig2 done')

# ============================ FIGURE 3: overall OOS accuracy incl. AI ============================
fig,axes=plt.subplots(1,2,figsize=(10,4.3),sharey=False)
for j,ds in enumerate(['m5','or2']):
    ov=pd.read_csv(fr'{RES}\{ds}_overall.csv').set_index('method').reindex(ORDER)
    ax=axes[j]
    bars=ax.bar(range(len(ORDER)),ov['mean_MASE'],color=[MCOL[m] for m in ORDER],edgecolor='k',lw=.6)
    ax.axhline(1.0,color='#C0392B',ls='--',lw=1); ax.text(0.1,1.02,'naïve benchmark (MASE=1)',color='#C0392B',fontsize=7.5)
    ax.set_xticks(range(len(ORDER))); ax.set_xticklabels([m.replace(' (AI)','\n(AI)') for m in ORDER],fontsize=8.5)
    ax.set_ylabel('mean OOS MASE  (lower = better)'); ax.set_title(DSNAME[ds],fontsize=10)
    for b,v in zip(bars,ov['mean_MASE']): ax.text(b.get_x()+b.get_width()/2,v+0.01,f'{v:.3f}',ha='center',fontsize=7.5)
    ax.set_ylim(0,max(ov['mean_MASE'])*1.18)
fig.suptitle('Figure 3.  Out-of-sample accuracy across both datasets. The global AI model (LightGBM) leads on M5; '
             'with strictly causal features, tuned simple smoothing leads on Online Retail II. Croston/SBA are '
             'weakest at this one-step horizon (see Section 5.10).',fontsize=9.5,y=1.02)
fig.tight_layout(); fig.savefig(fr'{FIG}\fig3_overall_mase.png'); plt.close(fig)
print('fig3 done')

# ============================ FIGURE 4: horses-for-courses by SBC class ============================
fig,axes=plt.subplots(1,2,figsize=(10,4.4))
CLASSES=['Smooth','Intermittent','Erratic','Lumpy']
for j,ds in enumerate(['m5','or2']):
    pbc=pd.read_csv(fr'{RES}\{ds}_by_class_pb.csv').set_index('class').reindex(CLASSES)
    ax=axes[j]; x=np.arange(len(CLASSES)); w=0.13
    for i,m in enumerate(ORDER):
        ax.bar(x+(i-2.5)*w,pbc[m],w,color=MCOL[m],edgecolor='k',lw=.3,label=m if j==0 else None)
    ax.set_xticks(x); ax.set_xticklabels(CLASSES,fontsize=9)
    ax.set_ylabel('Percentage-Best (%)'); ax.set_title(DSNAME[ds],fontsize=10)
fig.legend(ORDER,loc='upper center',ncol=6,fontsize=8,frameon=False,bbox_to_anchor=(0.5,1.07))
fig.suptitle('Figure 4.  Which method wins, by demand class (ties split fractionally). AI dominates every M5 class; '
             'on OR2 the zero-forecasting simple methods take the sparse Intermittent/Lumpy classes.',fontsize=9.5,y=1.005)
fig.tight_layout(rect=[0,0,1,0.98]); fig.savefig(fr'{FIG}\fig4_by_class.png'); plt.close(fig)
print('fig4 done')

# ============================ FIGURE 5: PB by demand-volume decile ============================
fig,axes=plt.subplots(1,2,figsize=(10,4.2))
for j,ds in enumerate(['m5','or2']):
    bv=pd.read_csv(fr'{RES}\{ds}_by_volume.csv')
    ax=axes[j]
    for m in ORDER:
        ax.plot(bv['decile'],bv[m],marker='o',ms=3.5,lw=1.6,color=MCOL[m],label=m)
    ax.set_xlabel('out-of-sample demand-volume decile (low → high)')
    ax.set_ylabel('Percentage-Best (%)'); ax.set_title(DSNAME[ds],fontsize=10)
    ax.set_xticks(range(1,11))
    if j==1: ax.legend(fontsize=7.5,frameon=False,ncol=2)
fig.suptitle('Figure 5.  Win-shares across demand-volume deciles. Simple methods own the near-zero tail; on M5 the '
             'AI model rises monotonically with density; on OR2, SBA peaks in its recurring mid-volume niche.',fontsize=9.5,y=1.02)
fig.tight_layout(); fig.savefig(fr'{FIG}\fig5_by_volume.png'); plt.close(fig)
print('fig5 done')

# ============================ FIGURE 6: robustness + feature importance ============================
fig,axes=plt.subplots(1,3,figsize=(12,3.9))
for j,ds in enumerate(['m5','or2']):
    rb=pd.read_csv(fr'{RES}\{ds}_robustness.csv')
    ax=axes[j]
    for m in ORDER:
        col = 'LightGBM' if m=='LightGBM (AI)' else m
        ax.plot(rb['test_weeks'],rb[col],marker='s',ms=4,lw=1.6,color=MCOL[m],label=m)
    ax.set_xlabel('hold-out window (weeks)'); ax.set_ylabel('mean OOS MASE')
    ax.set_title(f'{DSNAME[ds]}: ranking stability',fontsize=9.5)
    ax.set_xticks(rb['test_weeks'])
    if j==0: ax.legend(fontsize=7,frameon=False,ncol=2)
# feature importance (M5)
imp=pd.read_csv(fr'{RES}\m5_lgbm_importance.csv').head(10)[::-1]
ax=axes[2]
ax.barh(range(len(imp)),imp['gain']/imp['gain'].sum()*100,color=NAVY,edgecolor='k',lw=.4)
ax.set_yticks(range(len(imp))); ax.set_yticklabels(imp['feature'],fontsize=8)
ax.set_xlabel('% of total gain'); ax.set_title('LightGBM drivers (M5)',fontsize=9.5)
fig.suptitle('Figure 6.  Ranking is stable across hold-out horizons (left, centre). On M5 the AI model is driven '
             'overwhelmingly by recent-demand aggregates; price features carry under 1% of total gain (right).',
             fontsize=9.5,y=1.03)
fig.tight_layout(); fig.savefig(fr'{FIG}\fig6_robustness.png'); plt.close(fig)
print('fig6 done')
print('All figures saved to', FIG)
