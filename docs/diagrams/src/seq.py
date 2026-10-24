import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
plt.rcParams["font.family"]=["Liberation Sans","DejaVu Sans"]
NAVY="#12355b"; BLUE="#1f4e79"; FILL="#e8f1fa"; GOLD="#b8860b"; GFILL="#fff3dc"; GREY="#666666"

def draw(fname, title, sub, lifelines, steps, footer, W=12.0):
    """lifelines: list of (key,label,stereotype,kind) ; steps: list of dicts"""
    n=len(lifelines); left,right=1.3,W-1.3
    xs={k:left+i*(right-left)/(n-1) for i,(k,_,_,_) in enumerate(lifelines)}
    # first pass: compute height
    DY=0.52
    def height(ss):
        h=0
        for s in ss:
            t=s["t"]
            if t in("msg","ret","async"): h+=DY
            elif t=="self": h+=DY*1.25
            elif t=="note": h+=DY*0.9
            elif t=="frag": h+=DY*0.85+height(s["body"])+ (DY*0.55 if s.get("else") else 0)+(height(s["else"]) if s.get("else") else 0)+DY*0.3
        return h
    body_h=height(steps)
    top=2.55; bot=2.2
    H=top+body_h+bot
    fig=plt.figure(figsize=(W,H),dpi=200); ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,W); ax.set_ylim(H,0); ax.axis("off")
    ax.text(W/2,0.45,title,ha="center",va="center",fontsize=24,fontweight="bold",color=NAVY)
    ax.text(W/2,0.92,sub,ha="center",va="center",fontsize=13.5,fontweight="bold",color=BLUE)
    ax.text(W/2,1.28,"Experiment 6 — Sequence Diagram (derived from Experiments 3, 4 and 5)",ha="center",va="center",fontsize=10,style="italic",color=GREY)
    ytop=1.65
    # frame
    ax.add_patch(Rectangle((0.15,ytop-0.1),W-0.3,H-ytop-1.45,fill=False,ec="#999",lw=1.2))
    # heads
    hy=ytop+0.15
    ybody0=top+0.2
    yend=top+body_h+0.25
    for k,lab,st,kind in lifelines:
        x=xs[k]
        if kind=="actor":
            ax.add_patch(Circle((x,hy+0.12),0.1,fill=False,ec=NAVY,lw=1.6))
            ax.plot([x,x],[hy+0.22,hy+0.5],color=NAVY,lw=1.6); ax.plot([x-0.17,x+0.17],[hy+0.3,hy+0.3],color=NAVY,lw=1.6)
            ax.plot([x,x-0.13],[hy+0.5,hy+0.68],color=NAVY,lw=1.6); ax.plot([x,x+0.13],[hy+0.5,hy+0.68],color=NAVY,lw=1.6)
            ax.text(x,hy+0.84,lab,ha="center",va="center",fontsize=11.5,fontweight="bold",color=NAVY)
            ly0=hy+0.98
        else:
            ax.add_patch(FancyBboxPatch((x-0.78,hy),1.56,0.72,boxstyle="round,pad=0,rounding_size=0.06",fc=FILL,ec=BLUE,lw=1.5))
            ax.text(x,hy+0.2,st,ha="center",va="center",fontsize=8.5,style="italic",color=GREY)
            ax.text(x,hy+0.46,lab,ha="center",va="center",fontsize=11,fontweight="bold",color=NAVY)
            ly0=hy+0.72
        ax.plot([x,x],[ly0,yend],color="#7a8ca3",lw=1.2,ls=(0,(6,4)),zorder=1)
    act=[]  # activation boxes (key,y0,y1)
    state={"y":ybody0,"n":0}
    def lab(x1,x2,y,text,num):
        xm=(x1+x2)/2
        ax.text(xm,y-0.07,f"{num}: {text}" if num else text,ha="center",va="bottom",fontsize=8.8,color="#111",zorder=5,
                bbox=dict(fc="white",ec="none",pad=0.6,alpha=0.9))
    def render(ss,xl,xr):
        for s in ss:
            t=s["t"]; y=state["y"]
            if t in("msg","ret","async"):
                x1,x2=xs[s["f"]],xs[s["to"]]
                d=1 if x2>x1 else -1
                x1a,x2a=x1+d*0.06,x2-d*0.06
                if t=="ret":
                    ax.annotate("",xy=(x2a,y+0.3),xytext=(x1a,y+0.3),arrowprops=dict(arrowstyle="->",color=NAVY,lw=1.3,ls=(0,(5,3)),shrinkA=0,shrinkB=0),zorder=3)
                    lab(x1,x2,y+0.3,s["m"],None)
                else:
                    state["n"]+=1
                    style="-|>" if t=="msg" else "->"
                    ax.annotate("",xy=(x2a,y+0.3),xytext=(x1a,y+0.3),arrowprops=dict(arrowstyle=style,color=NAVY,lw=1.5,mutation_scale=13,shrinkA=0,shrinkB=0),zorder=3)
                    lab(x1,x2,y+0.3,s["m"],state["n"])
                    s["_n"]=state["n"]
                state["y"]+=DY
            elif t=="self":
                state["n"]+=1
                x=xs[s["f"]]
                ax.plot([x+0.06,x+0.55,x+0.55],[y+0.2,y+0.2,y+0.55],color=NAVY,lw=1.5,zorder=3)
                ax.annotate("",xy=(x+0.06,y+0.55),xytext=(x+0.55,y+0.55),arrowprops=dict(arrowstyle="-|>",color=NAVY,lw=1.5,mutation_scale=13,shrinkA=0,shrinkB=0))
                ax.text(x+0.62,y+0.38,f'{state["n"]}: {s["m"]}',ha="left",va="center",fontsize=8.8,zorder=5)
                state["y"]+=DY*1.25
            elif t=="note":
                x=xs[s["at"]]
                w=s.get("w",2.6)
                ax.add_patch(Rectangle((x-w/2,y+0.05),w,DY*0.7,fc="#fffbe6",ec=GOLD,lw=1))
                ax.text(x,y+0.05+DY*0.35,s["m"],ha="center",va="center",fontsize=8.5,style="italic",color="#5a4300")
                state["y"]+=DY*0.9
            elif t=="frag":
                y0=state["y"]
                state["y"]+=DY*0.85
                render(s["body"],xl,xr)
                ysplit=None
                if s.get("else"):
                    ysplit=state["y"]+0.05
                    state["y"]+=DY*0.55
                    render(s["else"],xl,xr)
                state["y"]+=DY*0.3
                y1=state["y"]-0.1
                fx0,fx1=s.get("x0",xl),s.get("x1",xr)
                ax.add_patch(Rectangle((fx0,y0+0.05),fx1-fx0,y1-y0-0.05,fill=False,ec=GOLD,lw=1.4,zorder=2))
                ax.add_patch(Rectangle((fx0,y0+0.05),0.6,0.26,fc=GFILL,ec=GOLD,lw=1.2,zorder=4))
                ax.text(fx0+0.3,y0+0.18,s["op"],ha="center",va="center",fontsize=9,fontweight="bold",color="#5a4300",zorder=5)
                ax.text(fx0+0.7,y0+0.2,"["+s["g"]+"]",ha="left",va="center",fontsize=9,style="italic",color="#5a4300",zorder=5)
                if ysplit:
                    ax.plot([fx0,fx1],[ysplit,ysplit],color=GOLD,lw=1.3,ls=(0,(6,3)),zorder=2)
                    ax.text(fx0+0.1,ysplit+0.17,"["+s["eg"]+"]",ha="left",va="center",fontsize=9,style="italic",color="#5a4300",zorder=5)
    render(steps,0.3,W-0.3)
    # legend
    ly=H-1.4
    ax.add_patch(Rectangle((W-6.35,ly),6.05,1.05,fc="white",ec="#999",lw=1))
    ax.text(W-6.2,ly+0.17,"Legend",fontsize=10,fontweight="bold",color=NAVY,va="center")
    def sample(y,style,ls,text):
        ax.annotate("",xy=(W-5.2,y),xytext=(W-6.2,y),arrowprops=dict(arrowstyle=style,color=NAVY,lw=1.4,ls=ls,mutation_scale=12,shrinkA=0,shrinkB=0))
        ax.text(W-5.08,y,text,fontsize=8.5,va="center",color=NAVY)
    sample(ly+0.42,"-|>","-","Synchronous message (numbered, in order)")
    sample(ly+0.64,"->","-","Asynchronous message (sender does not wait)")
    sample(ly+0.86,"->",(0,(5,3)),"Return message")
    ax.text(0.3,H-0.2,footer,fontsize=8.5,color=GREY,va="center")
    fig.savefig(fname,dpi=200,facecolor="white"); plt.close(fig)
    return H

LL1=[("S","Student","","actor"),("UI","Web Interface","«boundary»","obj"),("C","Platform Controller","«control»","obj"),("DB","Database","«entity»","obj")]
FOOT="Krishang Vikram Singh | Roll No. B106 | Batch C1 | B.Tech Computer Engineering"
def M(f,to,m): return dict(t="msg",f=f,to=to,m=m)
def R(f,to,m): return dict(t="ret",f=f,to=to,m=m)
def A(f,to,m): return dict(t="async",f=f,to=to,m=m)

s1=[
 M("S","UI","registerAccount(email, password)"),
 M("UI","C","createAccount(details)"),
 M("C","DB","findAccountByEmail(email)"),
 R("DB","C","no existing account"),
 M("C","DB","getCollegeByEmailDomain(email)"),
 R("DB","C","college record / null"),
 dict(t="self",f="C",m="verifyCollegeEmail()"),
 dict(t="frag",op="alt",g="college email valid",body=[
    M("C","DB","saveStudent(details, status = Verified)"),
    R("DB","C","studentId"),
    R("C","UI","registration successful"),
    R("UI","S","confirmation message"),
 ],**{"else":[
    R("C","UI","verification failed"),
    R("UI","S","error message"),
 ],"eg":"college email invalid"}),
 M("S","UI","login(email, password)"),
 M("UI","C","authenticate(email, password)"),
 M("C","DB","getUserByEmail(email)"),
 R("DB","C","userId, passwordHash"),
 dict(t="self",f="C",m="validateCredentials()"),
 dict(t="frag",op="alt",g="credentials valid",body=[
    R("C","UI","session started"),
    R("UI","S","home screen"),
 ],**{"else":[
    R("C","UI","authentication failed"),
    R("UI","S","error message"),
 ],"eg":"credentials invalid"}),
]
H1=draw("seq1.png","Sequence Diagram","Registration, College Verification and Login",LL1,s1,FOOT)
LL2=[("S","Student","","actor"),("UI","Web Interface","«boundary»","obj"),("C","Platform Controller","«control»","obj"),("DB","Database","«entity»","obj"),("A","Administrator","","actor")]
s2=[
 dict(t="note",at="S",m="Precondition: student is logged in",w=2.6),
 M("S","UI","searchRecommendations(category, location)"),
 M("UI","C","search(category, location)"),
 M("C","DB","queryRecommendations(category, cityId)"),
 R("DB","C","matching recommendations"),
 R("C","UI","results sorted by distance"),
 R("UI","S","list of recommendations"),
 M("S","UI","viewRecommendationDetails(recommendationId)"),
 M("UI","C","getDetails(recommendationId)"),
 M("C","DB","getRecommendationWithReviews(recommendationId)"),
 R("DB","C","details, average rating, published reviews"),
 R("C","UI","recommendation details"),
 R("UI","S","details page"),
 dict(t="frag",op="opt",g="student chooses to submit a review",body=[
    M("S","UI","submitReview(rating, comment)"),
    M("UI","C","submit(recommendationId, rating, comment)"),
    M("C","DB","saveReview(status = Pending)"),
    R("DB","C","reviewId"),
    A("C","A","notifyPendingReview(reviewId)"),
    M("A","C","validateReview(reviewId)"),
    M("C","DB","getReview(reviewId)"),
    R("DB","C","review content"),
    dict(t="frag",op="alt",g="review valid",x0=2.0,x1=12.5,body=[
        M("C","DB","updateReviewStatus(reviewId, Published)"),
        M("C","DB","calculateAverageRating(recommendationId)"),
        A("C","UI","notifyStudent(\"review published\")"),
    ],**{"else":[
        M("C","DB","updateReviewStatus(reviewId, Rejected)"),
        A("C","UI","notifyStudent(\"review rejected\")"),
    ],"eg":"review invalid"}),
    R("UI","S","review outcome message"),
 ]),
]
H2=draw("seq2.png","Sequence Diagram","Search, View Recommendation and Submit / Validate Review",LL2,s2,FOOT,W=13.0)
print(H1,H2)
