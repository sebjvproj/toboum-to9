****************************************************************
*  Moteur de sprites TO9 (repris de la démo, validé dans DCMOTO) :
*  mise à jour sans scintillement calée sur le faisceau, sprites compilés,
*  effacement par copie du décor, horloge au cycle près (timer 6846).
*  Le programme qui l'inclut définit : ESIZE, NMAX, BUFA/BUFB, ER16, BUFROW et les variables,
*  dont PALPTR (palette) et LZPA/LZPB (décor compressé) (voir toboum.asm).
*  Entités : 0 = héros, 1..NENN, puis NXTRA (0 ou 1) entité(s) en plus (la pièce éclair).
****************************************************************
ERASEALL
        LDU     #ENTS
        LDB     NENN
        INCB
        ADDB    NXTRA
EA1     PSHS    B
        LDA     2,U
        CMPA    #$FF
        BEQ     EA2
        LDB     3,U
        JSR     ERASE
EA2     LEAU    ESIZE,U
        PULS    B
        DECB
        BNE     EA1
        RTS

****************************************************************
* mise à jour sans scintillement. Le TO9 n'a qu'une page d'écran : un sprite ne doit
* jamais être en cours d'effacement/dessin quand le faisceau balaie ses lignes.
*  - chaque sprite est effacé puis redessiné d'un bloc ;
*  - 1er temps, dès le retour de trame : les sprites du bas, du haut vers le bas ; ils sont
*    finis avant que le faisceau (reparti du haut) les atteigne ;
*  - 2e temps, quand le faisceau a dépassé les autres (routine CLOCK, au cycle près) :
*    les sprites du haut, que le faisceau vient d'afficher.
*  Un effacement qui abîme un sprite déjà redessiné le fait redessiner aussitôt.
* Partage calculé à chaque image (sprites triés par ligne croissante, n = NACT) :
*  1er temps = les K sprites les plus bas, K le plus grand possible tel que le m-ième
*  (m = 1..K, traités de haut en bas) soit fini avant l'arrivée du faisceau :
*  m x COUT <= 112 + Y  (en lignes de 64 cycles ; retour de trame = 112 lignes ; COUT = coût
*  d'un sprite son compris, avec marge). 2e temps = les autres, dès que le faisceau a dépassé
*  le plus bas d'entre eux : CLOCK >= 112 + Ymax + 16 + MARGE lignes.
COUT    EQU     40              ; ~30 lignes mesurées (sprites compilés, son 1000 Hz) + marge
KMAX    EQU     7
* Calcul en un passage : le sprite j (rang dans ORDER, n sprites) a pour marge
*  112 + Y(j) - m x COUT = B(j) - K x COUT, avec B(j) = 112 + Y(j) + (n-1-j) x COUT ;
*  K tient si min B(j) >= K x COUT sur les K derniers ; on ajoute les sprites par le haut.
PLAN    JSR     SORT            ; ORDER, YS : lignes croissantes
        CLR     KK
        LDD     #$7FFF
        STD     MINB
        LDX     #YS
        LDB     NACT
        ABX                     ; X -> après le dernier (le plus bas)
UK1     LDA     KK              ; essai de K + 1 sprites
        CMPA    #KMAX
        BHS     UK5
        CMPA    NACT
        BHS     UK5
        LDB     #COUT
        MUL                     ; (n-1-j) x COUT, pour le sprite ajouté j = n-K-1
        ADDD    #112
        STD     TMPW
        LDB     ,-X             ; sa ligne
        CLRA
        ADDD    TMPW            ; B(j)
        CMPD    MINB
        BHS     UK2
        STD     MINB
UK2     LDA     KK
        INCA
        LDB     #COUT
        MUL                     ; (K+1) x COUT
        CMPD    MINB
        BHI     UK5             ; un sprite de plus ne tiendrait pas
        INC     KK
        BRA     UK1
UK5     LDA     NACT
        SUBA    KK
        STA     SPLITK
        LDD     #0              ; pas de 2e temps
        STD     T2L
        TST     SPLITK
        BEQ     UK9
        LDX     #YS
        LDB     SPLITK
        DECB
        LDB     B,X             ; Ymax du 2e temps
        CLRA
        ADDD    #112+16         ; le faisceau a dépassé Ymax+15 à 112+Ymax+16 lignes
        ADDD    MARGE
        STD     T2L
UK9     RTS

* exécution du plan, dès le retour de trame
UPDATE  LDX     #ENTS           ; aucun sprite encore traité
        LDB     NACT
UD0     CLR     10,X
        LEAX    ESIZE,X
        DECB
        BNE     UD0
        LDA     SPLITK
        STA     UPK
UD3     LDB     UPK             ; 1er temps : sprites du bas
        CMPB    NACT
        BHS     UD4
        JSR     PROCESS
        INC     UPK
        BRA     UD3
UD4     JSR     CLOCK           ; attendre que le faisceau ait dépassé les sprites du 2e temps
        CMPD    T2L
        BLO     UD4
        CLR     UPK             ; 2e temps : sprites du haut
UD5     LDB     UPK
        CMPB    SPLITK
        BHS     UD9
        JSR     PROCESS
        INC     UPK
        BRA     UD5
UD9     RTS

* traite le sprite ORDER[B] : effacement, réparation des voisins déjà traités, dessin
PROCESS LDX     #ORDER
        LDB     B,X
        JSR     ENTADR
        TFR     X,U
        LDA     2,U
        CMPA    #$FF
        BEQ     PR5
        LDB     3,U
        JSR     ERASE
        LDX     #ENTS           ; sprites déjà traités touchés par cet effacement ?
        LDB     NACT
PR1     TST     10,X
        BEQ     PR4
        LDA     ,X              ; |Pj - ancien Pk| < 4 paires
        SUBA    2,U
        BPL     PR2
        NEGA
PR2     CMPA    #4
        BHS     PR4
        LDA     1,X             ; |Yj - ancien Yk| < 16 lignes
        CMPA    3,U
        BHS     PR3
        LDA     3,U
        SUBA    1,X
        BRA     PR3B
PR3     SUBA    3,U
PR3B    CMPA    #16
        BHS     PR4
        PSHS    B,X,U
        TFR     X,U
        JSR     DRAWENT
        PULS    B,X,U
PR4     LEAX    ESIZE,X
        DECB
        BNE     PR1
PR5     LDA     #1
        STA     10,U
        JMP     DRAWENT

* dessine l'entité U à sa position et la mémorise
DRAWENT LDD     ,U
        STD     2,U
        LDY     6,U             ; image 1 ou 2 selon ITER
        LDA     ITER
        BITA    #8
        BEQ     DE1
        LDY     8,U
DE1     LDD     ,U
        JMP     DRAW

* B = n° d'entité -> X = son adresse
ENTADR  LDA     #ESIZE
        MUL
        ADDD    #ENTS
        TFR     D,X
        RTS

* ORDER = entités triées par ligne croissante, YS = leurs lignes (tri par insertion sur les
* deux tableaux à la fois : ni adresse d'entité ni multiplication dans les boucles)
SORT    LDB     NENN
        INCB
        ADDB    NXTRA
        STB     NACT
        LDX     #ENTS+1         ; ligne de l'entité 0
        LDU     #ORDER
        CLRA
SO1     STA     ,U
        LDB     ,X
        STB     YOFS,U          ; YS[i]
        LEAU    1,U
        LEAX    ESIZE,X
        INCA
        CMPA    NACT
        BNE     SO1
        LDB     NACT
        DECB
        BEQ     SO9
        STB     SI              ; éléments 1..n-1 à insérer
        LDU     #ORDER+1
SO2     LDA     YOFS,U
        STA     SKY
        LDA     ,U
        STA     SKEY
        PSHS    U
SO3     CMPU    #ORDER          ; décale vers le haut les lignes plus grandes
        BEQ     SO4
        LDA     YOFS-1,U
        CMPA    SKY
        BLS     SO4
        STA     YOFS,U
        LDA     -1,U
        STA     ,U
        LEAU    -1,U
        BRA     SO3
SO4     LDA     SKY
        STA     YOFS,U
        LDA     SKEY
        STA     ,U
        PULS    U
        LEAU    1,U
        DEC     SI
        BNE     SO2
SO9     RTS
* B = n° d'entité -> A = sa ligne
YOF     PSHS    X
        JSR     ENTADR
        LDA     1,X
        PULS    X,PC

****************************************************************
* affichage
* A = paire, B = ligne -> X = adresse écran (A conservé)
ADDR    PSHS    A
        LDA     #40
        MUL
        ADDD    #$4000
        TFR     D,X
        LDB     ,S
        LSRB
        ABX
        PULS    A,PC

* efface le sprite (A = paire, B = ligne) en recopiant la copie du décor
ERASE   PSHS    A,B
        JSR     ADDR
        LDA     1,S             ; Y copie = BUFA + (ligne-8)*29 + (paire/2 - 2)
        SUBA    #8
        LDB     #BUFROW
        MUL
        ADDD    #BUFA-2
        STD     TMPW
        LDB     ,S
        LSRB
        CLRA
        ADDD    TMPW
        TFR     D,Y
        LDA     ,S
        BITA    #1
        BNE     ERO
        JSR     ERBA
        LEAY    BUFB-BUFA,Y
        JSR     ERBB
        PULS    A,B,PC
ERO     LEAY    BUFB-BUFA,Y
        JSR     ERBB
        LEAX    1,X
        LEAY    BUFA-BUFB+1,Y
        JSR     ERBA
        PULS    A,B,PC

* dessine le sprite compilé Y (4 routines : banque 1 haut/bas, banque 2 haut/bas)
* en (A = paire, B = ligne)
DRAW    PSHS    Y
        JSR     ADDR
        PULS    Y
        BITA    #1
        BNE     DRO
        JSR     DRBA
        LEAY    4,Y
        JMP     DRBB
DRO     JSR     DRBB
        LEAX    1,X
        LEAY    4,Y
        JMP     DRBA

* une demi-case dans une banque vidéo, IRQ masquées pendant que PRC est modifié
ERBA    PSHS    CC
        ORCC    #$50
        LDA     PRC
        ORA     #1
        STA     PRC
        JSR     ER16
        PULS    CC,PC
ERBB    PSHS    CC
        ORCC    #$50
        LDA     PRC
        ANDA    #$FE
        STA     PRC
        JSR     ER16
        PULS    CC,PC
* dessin en deux moitiés : les IRQ passent entre les deux (plus de 500 cycles masqués
* ferait perdre une IRQ du timer : horloge et son faussés)
DRBA    PSHS    CC
        ORCC    #$50
        LDA     PRC
        ORA     #1
        STA     PRC
        JSR     [,Y]            ; moitié haute
        PULS    CC              ; les IRQ en attente sont servies ici
        PSHS    CC
        ORCC    #$50
        LDA     PRC
        ORA     #1
        STA     PRC
        JSR     [2,Y]           ; moitié basse
        PULS    CC,PC
DRBB    PSHS    CC
        ORCC    #$50
        LDA     PRC
        ANDA    #$FE
        STA     PRC
        JSR     [,Y]
        PULS    CC
        PSHS    CC
        ORCC    #$50
        LDA     PRC
        ANDA    #$FE
        STA     PRC
        JSR     [2,Y]
        PULS    CC,PC

* décor : décompression des deux banques (IRQ masquées)
SHOWDECOR
        LDA     PRC
        ORA     #1
        STA     PRC
        LDX     LZPA            ; données compressées de la banque A
        LDU     #$4000
        JSR     UNLZ
        LDA     PRC
        ANDA    #$FE
        STA     PRC
        LDX     LZPB            ; et de la banque B
        LDU     #$4000
        JMP     UNLZ
UNLZ    CMPU    #$5F40
        BHS     ULX
        LDB     ,X+
        BMI     ULM
        INCB
UL2     LDA     ,X+
        STA     ,U+
        DECB
        BNE     UL2
        BRA     UNLZ
ULM     ANDB    #$7F
        ADDB    #3
        STB     ULCNT
        LDD     ,X++
        STD     ULDIST
        PSHS    X
        TFR     U,D
        SUBD    ULDIST
        TFR     D,X
        LDB     ULCNT
UL3     LDA     ,X+
        STA     ,U+
        DECB
        BNE     UL3
        PULS    X
        BRA     UNLZ
ULX     RTS

* copie de l'aire de jeu (lignes 8..191, octets 2..30 de chaque banque)
SAVEBUF LDA     PRC
        ORA     #1
        STA     PRC
        LDU     #BUFA
        BSR     SB0
        LDA     PRC
        ANDA    #$FE
        STA     PRC
        LDU     #BUFB
SB0     LDX     #$4000+8*40+2
        LDA     #184
        STA     CNT
SB1     LDB     #BUFROW
SB2     LDA     ,X+
        STA     ,U+
        DECB
        BNE     SB2
        LEAX    40-BUFROW,X
        DEC     CNT
        BNE     SB1
        RTS

SETPAL  CLR     PALIDX
        CLRB
SP1     PSHS    B
        EORB    #8              ; le TO9 range l'entrée k dans la couleur k xor 8
        ASLB
        LDX     PALPTR          ; palette courante (16 x 2 octets)
        ABX
        LDA     ,X
        STA     PALDAT
        LDA     1,X
        STA     PALDAT
        PULS    B
        INCB
        CMPB    #16
        BNE     SP1
        RTS

WAITVBL PSHS    A,X
        LDX     #1250
WV1     LDA     GATE7
        BMI     WV2
        LEAX    -1,X
        BNE     WV1
        BRA     WV3
WV2     LDX     #1250
WV2B    LDA     GATE7
        BPL     WV3
        LEAX    -1,X
        BNE     WV2B
WV3     PULS    A,X,PC

INITVARS
        LDX     #VARS
IV1     CLR     ,X+
        CMPX    #VARSEND
        BLO     IV1
        RTS

****************************************************************
* horloge au cycle près : TIMEACC (+1000 à chaque IRQ) + position du compteur du 6846.
* Si le compteur ne se lit pas (CLKOK = 0), on se contente de TIMEACC (précision 1000
* cycles) et la marge MARGE est augmentée.
LATCH   EQU     999
* t = 0 : à appeler au retour de trame
CLKREF  PSHS    CC
        ORCC    #$50
        LDD     #0
        STD     TIMEACC
        TST     CLKOK
        BEQ     CR1
        LDD     TMSB            ; compteur (octet fort puis faible)
        STD     TMPW
        LDD     #LATCH
        SUBD    TMPW
CR1     STD     CLK0            ; décalage du compteur au moment de la référence
        PULS    CC,PC
* D = nombre de lignes (64 cycles) depuis la référence
CLOCK   TST     CLKOK
        BEQ     CK2
CK1     LDX     TIMEACC         ; lecture cohérente : TIMEACC n'a pas bougé pendant la lecture
        LDD     TMSB
        CMPX    TIMEACC
        BNE     CK1
        STD     TMPW
        LDD     #LATCH
        SUBD    TMPW
        LEAX    D,X
        TFR     X,D
        BRA     CK3
CK2     LDD     TIMEACC
CK3     SUBD    CLK0
        LSRA                    ; / 64
        RORB
        LSRA
        RORB
        LSRA
        RORB
        LSRA
        RORB
        LSRA
        RORB
        LSRA
        RORB
        RTS
* le compteur du 6846 se lit-il ? (deux lectures espacées doivent différer)
CLKTEST CLR     CLKOK
        LDD     #20
        STD     MARGE
        LDD     TMSB
        STD     TMPW
        LDB     #40
CT1     DECB
        BNE     CT1
        LDD     TMSB
        CMPD    TMPW
        BEQ     CT9
        INC     CLKOK
        LDD     #4              ; horloge précise : 4 lignes de marge suffisent
        STD     MARGE
CT9     RTS

