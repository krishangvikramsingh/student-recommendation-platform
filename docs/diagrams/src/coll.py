import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams["font.family"]=["Liberation Sans","DejaVu Sans"]
NAVY="#12355b"; BLUE="#1f4e79"; FILL="#e8f1fa"; GREY="#666666"; GOLD="#5a4300"
BW,BH=2.3,0.95
FOOT="Krishang Vikram Singh | Roll No. B106 | Batch C1 | B.Tech Computer Engineering"

def draw(fname,sub,nodes,links,selfs,H,W=12.0):
    fig=plt.figure(figsize=(W,H),dpi=200); ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,W); ax.set_ylim(H,0); ax.axis("off")
    ax.text(W/2,0.45,"Collaboration Diagram",ha="center",va="center",fontsize=24,fontweight="bold",color=NAVY)
    ax.text(W/2,0.92,sub,ha="center",va="center",fontsize=13.5,fontweight="bold",color=BLUE)
    ax.text(W/2,1.28,"Experiment 7 — Collaboration Diagram (derived from Experiments 3, 5 and 6)",ha="center",va="center",fontsize=10,style="italic",color=GREY)
    ax.add_patch(Rectangle((0.15,1.55),W-0.3,H-1.55-1.5,fill=False,ec="#999",lw=1.2))
    for k,(x,y,lab,st) in nodes.items():
        ax.add_patch(Rectangle((x-BW/2,y-BH/2),BW,BH,fc=FILL,ec=BLUE,lw=1.6,zorder=3))
        ax.text(x,y-0.27,st,ha="center",va="center",fontsize=8.5,style="italic",color=GREY,zorder=4)
        ax.text(x,y+0.08,lab,ha="center",va="center",fontsize=10.5,fontweight="bold",color=NAVY,zorder=4)
        tw=len(lab)*0.082
        ax.plot([x-tw/2,x+tw/2],[y+0.22,y+0.22],color=NAVY,lw=1,zorder=4)
    def edge(a,b):
        (x1,y1,_,_),(x2,y2,_,_)=nodes[a],nodes[b]
        if abs(y1-y2)<1e-6:
            d=1 if x2>x1 else -1; return (x1+d*BW/2,y1),(x2-d*BW/2,y2)
        d=1 if y2>y1 else -1; return (x1,y1+d*BH/2),(x2,y2-d*BH/2)
    def arrow(p,q,col=NAVY,filled=True):
        ax.annotate("",xy=q,xytext=p,arrowprops=dict(arrowstyle="-|>" if filled else "->",color=col,lw=1.5,mutation_scale=12,shrinkA=0,shrinkB=0),zorder=5)
    for (a,b,msgs) in links:
        p,q=edge(a,b); ax.plot([p[0],q[0]],[p[1],q[1]],color=NAVY,lw=1.8,zorder=2)
        horiz=abs(p[1]-q[1])<1e-6
        if horiz:
            xm=(p[0]+q[0])/2; ups=[m for m in msgs if m[3]=="up"]; dns=[m for m in msgs if m[3]=="dn"]
            for rows,sgn in((ups,-1),(dns,1)):
                for i,(num,txt,fwd,_,asy) in enumerate(rows):
                    y=p[1]+sgn*(0.27+0.27*((len(rows)-1-i) if sgn<0 else i))
                    s=f"{num}: {txt}"
                    w=len(s)*0.071+0.7
                    x0=xm-w/2
                    d=(1 if q[0]>p[0] else -1)*(1 if fwd else -1)
                    a0,a1=(x0,x0+0.5) if d>0 else (x0+0.5,x0)
                    arrow((a0,y),(a1,y),filled=not asy)
                    ax.text(x0+0.6,y,s,ha="left",va="center",fontsize=8.8,color="#111",zorder=5)
        else:
            ym=(p[1]+q[1])/2; n=len(msgs); xl=p[0]-0.25
            for i,(num,txt,fwd,_,asy) in enumerate(msgs):
                y=ym+(i-(n-1)/2)*0.4
                s=f"{num}: {txt}"
                d=(1 if q[1]>p[1] else -1)*(1 if fwd else -1)
                ax.annotate("",xy=(p[0]-0.12,y+0.14*d),xytext=(p[0]-0.12,y-0.14*d),arrowprops=dict(arrowstyle="-|>" if not asy else "->",color=NAVY,lw=1.4,mutation_scale=11,shrinkA=0,shrinkB=0),zorder=5)
                ax.text(xl-0.1,y,s,ha="right",va="center",fontsize=8.8,color="#111",zorder=5)
    for k,items in selfs.items():
        x,y,_,_=nodes[k]
        yb=y+BH/2
        ax.plot([x-0.6,x-0.6,x+0.6,x+0.6],[yb,yb+0.4,yb+0.4,yb],color=NAVY,lw=1.8,zorder=2)
        arrow((x+0.6,yb+0.4),(x+0.6,yb+0.01))
        for i,(num,txt) in enumerate(items):
            ax.text(x,yb+0.7+0.3*i,f"{num}: {txt}",ha="center",va="center",fontsize=8.8,zorder=5)
    # legend
    ly=H-1.4
    ax.add_patch(Rectangle((W-6.35,ly),6.05,1.05,fc="white",ec="#999",lw=1))
    ax.text(W-6.2,ly+0.17,"Legend",fontsize=10,fontweight="bold",color=NAVY,va="center")
    ax.add_patch(Rectangle((W-6.2,ly+0.36),0.45,0.22,fc=FILL,ec=BLUE,lw=1.2)); ax.text(W-5.65,ly+0.47,"Object (name : Class), joined by a link",fontsize=8.5,va="center",color=NAVY)
    ax.annotate("",xy=(W-5.75,ly+0.7),xytext=(W-6.2,ly+0.7),arrowprops=dict(arrowstyle="-|>",color=NAVY,lw=1.4,mutation_scale=11,shrinkA=0,shrinkB=0)); ax.text(W-5.65,ly+0.7,"Synchronous message; number shows order and nesting",fontsize=8.5,va="center",color=NAVY)
    ax.annotate("",xy=(W-5.75,ly+0.92),xytext=(W-6.2,ly+0.92),arrowprops=dict(arrowstyle="->",color=NAVY,lw=1.4,mutation_scale=11,shrinkA=0,shrinkB=0)); ax.text(W-5.65,ly+0.92,"Asynchronous message;  [guard] = condition",fontsize=8.5,va="center",color=NAVY)
    ax.text(0.3,H-0.2,FOOT,fontsize=8.5,color=GREY,va="center")
    fig.savefig(fname,dpi=200,facecolor="white"); plt.close(fig)

# messages: (num,text,forward?,pos,async)
def m(n,t,fwd=True,pos="up",asy=False): return (n,t,fwd,pos,asy)
nodes1={"S":(2.2,3.0,"s : Student","«actor»"),"UI":(9.8,3.0,"ui : WebInterface","«boundary»"),"C":(9.8,7.2,"ctrl : PlatformController","«control»"),"DB":(2.2,7.2,"db : Database","«entity»")}
links1=[("S","UI",[m("1","registerAccount(email, password)",pos="up"),m("1.2","[email valid] showConfirmation()",False,"up"),m("1.3","[email invalid] showError()",False,"up"),
                   m("2","login(email, password)",pos="dn"),m("2.2","[credentials valid] showHomeScreen()",False,"dn"),m("2.3","[credentials invalid] showError()",False,"dn")]),
        ("UI","C",[m("1.1","createAccount(details)"),m("2.1","authenticate(email, password)")]),
        ("C","DB",[m("1.1.1","findAccountByEmail(email)",pos="up"),m("1.1.2","getCollegeByEmailDomain(email)",pos="up"),m("1.1.4","[email valid] saveStudent(details, Verified)",pos="up"),
                   m("2.1.1","getUserByEmail(email)",pos="dn")])]
selfs1={"C":[("1.1.3","verifyCollegeEmail()"),("2.1.2","validateCredentials()")]}
# C is at right edge; self-loop would run off; mirror: place loop on C bottom instead -> use selfs on left? keep W wide enough
draw("coll1.png","Registration, College Verification and Login",nodes1,links1,selfs1,H=11.0,W=13.0)

nodes2={"S":(2.2,3.0,"s : Student","«actor»"),"UI":(10.0,3.0,"ui : WebInterface","«boundary»"),"C":(10.0,7.2,"ctrl : PlatformController","«control»"),"DB":(2.2,7.2,"db : Database","«entity»"),"A":(10.0,11.4,"admin : Administrator","«actor»")}
links2=[("S","UI",[m("1","searchRecommendations(category, location)",pos="up"),m("1.2","showResults(sorted by distance)",False,"up"),
                   m("2","viewRecommendationDetails(recommendationId)",pos="up"),m("2.2","showDetails()",False,"up"),
                   m("3","[student chooses to review] submitReview(rating, comment)",pos="dn"),m("3.2","showReviewOutcome()",False,"dn")]),
        ("UI","C",[m("1.1","search(category, location)"),m("2.1","getDetails(recommendationId)"),m("3.1","submit(recommendationId, rating, comment)"),m("3.1.3.5","notifyStudent(outcome)",False,asy=True)]),
        ("C","DB",[m("1.1.1","queryRecommendations(category, cityId)",pos="up"),m("2.1.1","getRecommendationWithReviews(recommendationId)",pos="up"),m("3.1.1","saveReview(status = Pending)",pos="up"),
                   m("3.1.3.1","getReview(reviewId)",pos="dn"),m("3.1.3.2","[review valid] updateReviewStatus(reviewId, Published)",pos="dn"),
                   m("3.1.3.3","[review valid] calculateAverageRating(recommendationId)",pos="dn"),m("3.1.3.4","[review invalid] updateReviewStatus(reviewId, Rejected)",pos="dn")]),
        ("C","A",[m("3.1.2","notifyPendingReview(reviewId)",asy=True),m("3.1.3","validateReview(reviewId)",False)])]
draw("coll2.png","Search, View Recommendation and Submit / Validate Review",nodes2,links2,{},H=13.8,W=13.0)
