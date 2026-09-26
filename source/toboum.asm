****************************************************************
*  TOboum - jeu de plates-formes pour Thomson TO9
*  Assembleur 6809, mode 160x200 16 couleurs, matériel original.
*
*  Toto à la casquette à hélice ramasse les 18 bombes du niveau (la bombe
*  allumée rapporte double et allume la suivante) en évitant les ennemis.
*  Flèches gauche/droite : marcher (en l'air, Toto garde son élan)
*  Flèche haut ou ESPACE : sauter ; maintenue en descente : chute lente ;
*  nouvel appui en l'air : freiner (on plane en tapotant)
*  Flèche bas : en l'air, arrêter l'élan     S : bruitages oui/non
*  Manette 1 : directions + bouton (saut)
*
*  Mémoire : programme et données $A000-$DFFF ; copie de l'aire de jeu $6400-$8DAF ;
*            fonds sous les bombes $8DB0- ; variables ensuite ; pile sous $A000
****************************************************************
PUTC    EQU     $E803
GETC    EQU     $E806
STATUS  EQU     $6019
TIMEPT  EQU     $6027
IRQEXIT EQU     $E830
PRC     EQU     $E7C3
TCR     EQU     $E7C5
TMSB    EQU     $E7C6
KTEST   EQU     $E7C8
JOYDIR  EQU     $E7CC           ; PIA jeux, port A : directions (0 = appuyé)
DAC     EQU     $E7CD           ; port B : bits 0-5 = CNA, bit 6 = bouton manette 1
JOYCRA  EQU     $E7CE
DACCR   EQU     $E7CF
PALDAT  EQU     $E7DA
PALIDX  EQU     $E7DB
VMODE   EQU     $E7DC
BORDER  EQU     $E7DD
GATE7   EQU     $E7E7
* lecture de secteurs de disquette par le moniteur
DKCO    EQU     $E82A
DKOPC   EQU     $6048           ; opération (2 = lire un secteur)
DKDRV   EQU     $6049           ; lecteur
DKTRK   EQU     $604A           ; piste (16 bits)
DKSEC   EQU     $604C           ; secteur (1 à 16)
DKBUF   EQU     $604F           ; adresse de destination (256 octets)

BUFA    EQU     $6400           ; copie de l'aire de jeu (184 lignes x 29 octets par banque)
BUFB    EQU     BUFA+184*29
BUFEND  EQU     BUFB+184*29
PATCH   EQU     BUFEND          ; fond propre sous chaque bombe : 64 octets par bombe
PMIN    EQU     4               ; aire de jeu en paires (2 pixels) : x 8..123
PMAX    EQU     58
YMIN    EQU     8
YMAX    EQU     176             ; sol : pieds en ligne 192
NMAX    EQU     8
ESIZE   EQU     16              ; P, Y, ancien P, ancien Y, dP, dY, image 1, image 2,
*                                 fait, type, compteur
T_ROBOT EQU     1
T_CHAUV EQU     2
T_BOULE EQU     3
T_NUAGE EQU     4
* physique de Toto (lignes x 256 par top de 1/50 s), façon arcade : saut de ~114 lignes
* (les 2/3 de l'aire de jeu) ; bas tenu double la gravité (saut court, chute rapide) ;
* haut tenu en descente la divise par 2 (chute lente) ; un nouvel appui en l'air freine
VMARCHE EQU     102             ; marche : 102/256 = 0,4 paire par top = 40 pixels/s
GRAV    EQU     $000E           ; 0,055 ligne/top²
SAUT    EQU     $0378           ; 3,47 lignes/top au décollage
CHUTEMX EQU     $0400           ; chute limitée à 4 lignes/top
* états de la partie
G_JEU   EQU     0
G_MORT  EQU     1
G_BRAVO EQU     2
G_FIN   EQU     3
C_BLANC EQU     8
C_JAUNE EQU     11
C_ROUGE EQU     12

        ORG     $A000
START   LDB     #$14            ; curseur invisible
        JSR     PUTC
        ORCC    #$50
        LDS     #$9FF0
        JSR     INITVARS
        LDX     #PALNOIR        ; écran noir jusqu'au premier décor
        STX     PALPTR
        LDA     #$7B
        STA     VMODE
        CLR     BORDER
        JSR     SETPAL
        JSR     INITJOY
        JSR     SNDON           ; démasque les IRQ
        JSR     CLKTEST
        JSR     NEWGAME
        JSR     PLAN            ; premier plan d'affichage
* boucle : au retour de trame, mise à jour des sprites ; puis la logique, top par top
LOOP    JSR     WAITVBL
        JSR     CLKREF
        JSR     UPDATE
UPDONE  JSR     READIN
        LDB     TICK            ; nombre de tops (1/50 s) depuis le dernier tour
        TFR     B,A
        SUBB    LTICK
        STA     LTICK
        CMPB    #4              ; au plus 4 tops de retard rattrapés
        BLS     LP1
        LDB     #4
LP1     STB     NTICK
        BEQ     LP3
LP2     JSR     TICKLOG
        DEC     NTICK
        BNE     LP2
LP3     JSR     SHOWSTATS
        JSR     PLAN
        INC     ITER
        BRA     LOOP

****************************************************************
* entrées : clavier (une touche à la fois) et manette -> IN_L, IN_R, IN_U, IN_D
READIN  CLR     IN_L
        CLR     IN_R
        CLR     IN_U
        CLR     IN_D
        LDA     KTEST
        BITA    #1
        BNE     RI1
        CLR     LASTKEY
RI1     JSR     GETC
        TSTB
        BEQ     RI3
        CMPB    #'S
        BEQ     RI2
        CMPB    #'s
        BNE     RI2B
RI2     JSR     SNDTOGGLE
        BRA     RI3
RI2B    STB     LASTKEY
RI3     LDB     LASTKEY
        CMPB    #$08
        BNE     RI4
        INC     IN_L
RI4     CMPB    #$09
        BNE     RI5
        INC     IN_R
RI5     CMPB    #$0B
        BEQ     RI6
        CMPB    #$20
        BNE     RI7
RI6     INC     IN_U
RI7     CMPB    #$0A
        BNE     RI8
        INC     IN_D
RI8     TST     JOYOK
        BEQ     RI9
        LDA     JOYDIR
        BITA    #$01
        BNE     RJ1
        INC     IN_U
RJ1     BITA    #$02
        BNE     RJ2
        INC     IN_D
RJ2     BITA    #$04
        BNE     RJ3
        INC     IN_L
RJ3     BITA    #$08
        BNE     RJ4
        INC     IN_R
RJ4     LDA     DAC
        BITA    #$40
        BNE     RI9
        INC     IN_U
RI9     RTS

* manette présente ? (comme TOetris : le bit 2 du registre de contrôle se relit)
INITJOY CLR     JOYOK
        LDA     JOYCRA
        ORA     #$04
        STA     JOYCRA
        LDB     JOYCRA
        ANDA    #$3F
        ANDB    #$3F
        PSHS    A
        CMPB    ,S+
        BNE     IJ9
        INC     JOYOK
IJ9     RTS

****************************************************************
* parties et niveaux
NEWGAME LDD     #0
        STD     SCORE
        STA     SCORE+2
        LDA     #3
        STA     LIVES
        LDA     #1
        STA     LEVELB
        STA     LEVELN
        JMP     NEWLEVEL

* nouveau niveau : décor, bombes (dessinées dans la copie du décor), Toto au départ
NEWLEVEL
        JSR     TOTORESET       ; d'abord : Toto et ennemis « jamais dessinés »
        CLR     NENN
        CLR     BORDER
        LDX     #PALNOIR        ; écran noir pendant la préparation
        STX     PALPTR
        JSR     SETPAL
        PSHS    CC
        ORCC    #$50
        JSR     CHOOSEDECOR     ; décor du niveau (lu sur la disquette si besoin)
        JSR     SHOWDECOR
        JSR     SAVEBUF
        CLRA                    ; fond propre sous chaque bombe
NL1     STA     BIDX
        JSR     PATCHSAVE
        LDX     #BSTATE
        LDA     BIDX
        LDB     #1
        STB     A,X
        INCA
        CMPA    #NBOMB
        BNE     NL1
        CLR     LIT             ; la bombe 0 est allumée
        CLRA
NL2     STA     BIDX
        JSR     BOMBSHOW
        LDA     BIDX
        INCA
        CMPA    #NBOMB
        BNE     NL2
        PULS    CC
        LDX     NEWPAL          ; le décor est prêt : ses couleurs
        STX     PALPTR
        JSR     SETPAL
        LDA     #NBOMB
        STA     BLEFT
        LDA     LEVELN          ; ennemis au plus : niveau + 3 (8 au maximum)
        ADDA    #3
        CMPA    #NMAX
        BLS     NL3
        LDA     #NMAX
NL3     STA     NMAXLV
        LDA     #1              ; ennemis plus rapides à partir du niveau 3
        LDB     LEVELN
        CMPB    #3
        BHS     NL4
        LDA     #3
NL4     STA     SPDMASK
        CLR     NSPAWN
        LDA     #50
        STA     INVUL
        LDA     #G_JEU
        STA     GSTATE
        LDA     #1
        STA     DIRTY
        LDX     #SFX_NIVEAU
        JMP     PLAYSFX

* décor du niveau : n° (niveau - 1) modulo NDECOR, lu sur la disquette (DECORS.DAT, secteurs
* bruts) dans la copie de l'aire de jeu, libre à ce moment-là (SAVEBUF la réécrit ensuite).
* En cas d'erreur de lecture : aire de jeu vide (fond noir) et palette de secours.
CHOOSEDECOR
        LDA     LEVELN
        DECA
CD1     CMPA    #NDECOR
        BLO     CD2
        SUBA    #NDECOR
        BRA     CD1
CD2     STA     DECN
        JSR     LOADDECOR
        BCS     CD8
        LDX     #BUFA           ; palette (copiée à part : SAVEBUF réécrira cette zone),
        LDU     #PALRAM         ; puis position de la banque B, puis banque A
        LDB     #32
CD3     LDA     ,X+
        STA     ,U+
        DECB
        BNE     CD3
        LDX     #PALRAM
        STX     NEWPAL
        LDX     #BUFA+34
        STX     LZPA
        LDD     BUFA+32
        ADDD    #BUFA
        STD     LZPB
        RTS
CD8     LDX     #PALSECOURS
        STX     NEWPAL
        LDX     #DECVIDE        ; décor vide : 8000 octets nuls par banque
        STX     LZPA
        STX     LZPB
        RTS
* « décor » compressé vide : 63 copies de 130 octets + littéraux (UNLZ s'arrête à 8000)
DECVIDE FCB     $00,$00         ; 1 octet nul
        FCB     $FF,$00,$01     ; copie de 130 octets à distance 1 (le zéro précédent)...
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01
        FCB     $FF,$00,$01

* lit le décor DECN (0..) : DECTAB donne 1er secteur et nombre de secteurs depuis la piste
* DATTRK secteur 1 ; C = 1 si erreur
LOADDECOR
        LDX     #DECTAB
        LDA     DECN
        ASLA
        LEAX    A,X
        LDB     1,X
        STB     CNT             ; nombre de secteurs
        LDB     ,X              ; 1er secteur (linéaire)
        CLRA
        TFR     B,A             ; piste = DATTRK + secteur / 16, secteur = reste + 1
        LSRA
        LSRA
        LSRA
        LSRA
        ADDA    #DATTRK
        STA     LDTRK
        ANDB    #15
        INCB
        STB     LDSEC
        LDX     #BUFA
LD1     LDA     #2
        STA     DKOPC
        CLR     DKDRV
        CLR     DKTRK
        LDA     LDTRK
        STA     DKTRK+1
        LDA     LDSEC
        STA     DKSEC
        STX     DKBUF
        PSHS    X
        JSR     DKCO
        PULS    X
        BCS     LD9
        LEAX    256,X
        INC     LDSEC
        LDA     LDSEC
        CMPA    #17
        BNE     LD2
        LDA     #1
        STA     LDSEC
        INC     LDTRK
LD2     DEC     CNT
        BNE     LD1
        ANDCC   #$FE
LD9     RTS
PALNOIR FCB     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
        FCB     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

* Toto au point de départ, plus d'ennemis à l'écran (tous marqués « jamais dessinés »)
TOTORESET
        LDX     #ENTS
        LDB     #NMAX+1
TR1     LDA     #$FF
        STA     2,X
        LEAX    ESIZE,X
        DECB
        BNE     TR1
        LDU     #ENTS
        LDD     #DEPP*256+DEPY
        STD     ,U
        CLR     TYF
        LDD     #0
        STD     TVY
        CLR     TVX
        CLR     FACE
        LDA     #1
        STA     ONGND
        LDA     #50
        STA     SPT
        JMP     TOTOIMG

****************************************************************
* un top de logique (1/50 s)
TICKLOG LDA     GSTATE
        BEQ     TL1
        DEC     GTIMER
        BNE     TL0
        CMPA    #G_MORT
        LBEQ    AFTERDEATH
        CMPA    #G_BRAVO
        BEQ     TLNEXT
        JMP     NEWGAME         ; fin de partie : on recommence
TL0     RTS
TLNEXT  LDA     LEVELB          ; niveau suivant (BCD et binaire)
        ADDA    #1
        DAA
        STA     LEVELB
        INC     LEVELN
        JMP     NEWLEVEL
TL1     JSR     TOTOTICK
        JSR     ENNTICK
        JSR     SPAWNTICK
        JSR     COLLIDE
        JMP     BOMBCHK

****************************************************************
* Toto : marche, saut, vol plané, plateformes
TOTOTICK
        LDU     #ENTS
        LDA     IN_L            ; direction voulue
        BEQ     TT1
        LDA     #-1
        STA     TVX
        LDA     #1
        STA     FACE
        BRA     TT3
TT1     LDA     IN_R
        BEQ     TT2
        LDA     #1
        STA     TVX
        CLR     FACE
        BRA     TT3
TT2     TST     ONGND           ; au sol : pas de touche = arrêt ; en l'air : élan conservé
        BEQ     TT2B
        TST     IN_U            ; ... sauf si un saut part maintenant : il garde l'élan
        BEQ     TT2A            ; (le clavier ne voit que la dernière touche : droite
        TST     JLATCH          ;  maintenue puis haut = saut en biais)
        BEQ     TT2B
TT2A    CLR     TVX
TT2B    TST     IN_D
        BEQ     TT3
        CLR     TVX
TT3     LDA     HXC             ; pas horizontal au rythme VMARCHE (fraction de paire par top)
        ADDA    #VMARCHE
        STA     HXC
        BCC     TT5             ; pas de retenue : pas de pas ce top-ci
        LDA     ,U
        ADDA    TVX
        CMPA    #PMIN
        BLT     TT4
        CMPA    #PMAX
        BGT     TT4
        PSHS    A
        LDB     1,U
        JSR     BLOCKED         ; une plateforme sur le côté ?
        PULS    A
        BCS     TT4
        STA     ,U
        BRA     TT5
TT4     CLR     TVX
* saut (à chaque NOUVEL appui) : au sol il décolle, en l'air il freine (vitesse verticale nulle)
TT5     TST     IN_U
        BNE     TT6
        CLR     JLATCH
        BRA     TT7
TT6     TST     JLATCH          ; touche déjà tenue : pas un nouvel appui
        BNE     TT7
        INC     JLATCH
        TST     ONGND
        BEQ     TT6B
        LDD     #-SAUT          ; décollage
        STD     TVY
        CLR     ONGND
        LDX     #PTS10          ; +10 points par décollage
        JSR     ADDSCORE
        LDA     #1
        STA     DIRTY
        LDX     #SFX_SAUT
        JSR     PLAYSFX
        BRA     TT7
TT6B    LDD     #0              ; en l'air : frein
        STD     TVY
TT7     TST     ONGND
        LBNE    TT20
* en l'air : gravité ; bas : x2 (saut court, chute rapide) ; haut tenu en DESCENTE : /2
* (chute lente, image « hélice ») ; en montée, haut ne change rien : saut aux 2/3 de l'écran
        CLR     GLIDE
        LDX     #GRAV
        TST     IN_D
        BEQ     TT7B
        LDX     #GRAV*2
        BRA     TT8
TT7B    TST     IN_U
        BEQ     TT8
        LDD     TVY
        BMI     TT8             ; en montée : gravité normale
        LDX     #GRAV/2
        INC     GLIDE
TT8     STX     TMPW
        LDD     TVY
        ADDD    TMPW
        CMPD    #CHUTEMX
        BLE     TT9
        LDD     #CHUTEMX
TT9     STD     TVY
        LDA     1,U             ; ancienne ligne
        STA     OLDY
        LDB     TYF
        ADDD    TVY
        STB     TYF
        STA     NEWY            ; (TVY >= -5 lignes : pas de passage sous zéro)
        LDD     TVY
        BMI     TT12
* descente : se pose-t-il ?
        LDA     ,U
        LDB     OLDY
        JSR     LANDCHK
        BCC     TT10
        STB     1,U
        CLR     TYF
        LDD     #0
        STD     TVY
        LDA     #1
        STA     ONGND
        BRA     TT30
TT10    LDA     NEWY
        STA     1,U
        BRA     TT30
* montée : se cogne-t-il ?
TT12    LDA     ,U
        LDB     OLDY
        JSR     HEADCHK
        BCC     TT13
        STB     1,U
        CLR     TYF
        LDD     #0
        STD     TVY
        BRA     TT30
TT13    LDA     NEWY
        CMPA    #YMIN
        BHS     TT14
        LDA     #YMIN
        CLR     TYF
        LDD     #0
        STD     TVY
        LDA     #YMIN
TT14    STA     1,U
        BRA     TT30
* au sol : tombe-t-il (plus rien sous les pieds) ?
TT20    LDA     ,U
        LDB     1,U
        JSR     SUPPORT
        BCS     TT30
        CLR     ONGND
        LDD     #0
        STD     TVY
TT30    JMP     TOTOIMG

* images de Toto selon son état
TOTOIMG LDU     #ENTS
        LDA     GSTATE
        CMPA    #G_MORT
        BNE     TI1
        LDX     #SPR_TOTO_PERDU
        TFR     X,Y
        BRA     TI9
TI1     TST     ONGND
        BEQ     TI4
        TST     FACE            ; au sol : marche (ou arrêt)
        BNE     TI2
        LDX     #SPR_TOTO_M1D
        LDY     #SPR_TOTO_M2D
        BRA     TI3
TI2     LDX     #SPR_TOTO_M1G
        LDY     #SPR_TOTO_M2G
TI3     TST     TVX
        BNE     TI9
        TFR     X,Y             ; arrêté : une seule image
        BRA     TI9
TI4     LDD     TVY             ; en l'air : hélice si montée ou vol plané, sinon chute
        BMI     TI5
        TST     GLIDE
        BNE     TI5
        LDX     #SPR_TOTO_CH
        TFR     X,Y
        BRA     TI9
TI5     TST     FACE
        BNE     TI6
        LDX     #SPR_TOTO_V1D
        LDY     #SPR_TOTO_V2D
        BRA     TI9
TI6     LDX     #SPR_TOTO_V1G
        LDY     #SPR_TOTO_V2G
TI9     STX     6,U
        STY     8,U
        RTS

* A = paire, B = ancienne ligne, NEWY = nouvelle ligne (descente) :
* C = 1 et B = ligne d'arrivée si les pieds franchissent le sol ou le dessus d'une plateforme
LANDCHK STA     CP
        STB     CY
        LDA     NEWY
        CMPA    #YMAX
        BLO     LC1
        LDB     #YMAX
        ORCC    #1
        RTS
LC1     LDX     #PLATS
        LDA     #NPLAT
        STA     CNT
LC2     JSR     OVERLAP
        BCC     LC3
        LDA     CY              ; ancien pied (Y+16) <= dessus < = nouveau pied
        ADDA    #16
        CMPA    2,X
        BHI     LC3
        LDA     NEWY
        ADDA    #16
        CMPA    2,X
        BLO     LC3
        LDB     2,X
        SUBB    #16
        ORCC    #1
        RTS
LC3     LEAX    3,X
        DEC     CNT
        BNE     LC2
        ANDCC   #$FE
        RTS

* A = paire, B = ancienne ligne, NEWY (montée) : C = 1 et B = ligne sous la plateforme
HEADCHK STA     CP
        STB     CY
        LDX     #PLATS
        LDA     #NPLAT
        STA     CNT
HC1     JSR     OVERLAP
        BCC     HC2
        LDA     2,X             ; dessous = dessus + 4
        ADDA    #4
        CMPA    CY
        BHI     HC2
        CMPA    NEWY
        BLS     HC2
        TFR     A,B
        ORCC    #1
        RTS
HC2     LEAX    3,X
        DEC     CNT
        BNE     HC1
        ANDCC   #$FE
        RTS

* A = paire, B = ligne : C = 1 si les pieds reposent sur le sol ou une plateforme
SUPPORT CMPB    #YMAX
        BHS     SU8
        STA     CP
        ADDB    #16
        STB     CYB             ; ligne des pieds
        LDX     #PLATS
        LDB     #NPLAT
SU1     LDA     CYB
        CMPA    2,X
        BNE     SU2
        JSR     OVERLAP
        BCS     SU8
SU2     LEAX    3,X
        DECB
        BNE     SU1
        ANDCC   #$FE
        RTS
SU8     ORCC    #1
        RTS

* le sprite en paire CP chevauche-t-il la plateforme X (au moins 2 paires) ? -> C
OVERLAP LDA     CP
        ADDA    #2
        CMPA    ,X
        BLO     OV9
        LDA     CP
        INCA
        CMPA    1,X
        BHS     OV9
        ORCC    #1
        RTS
OV9     ANDCC   #$FE
        RTS

* A = paire, B = ligne : C = 1 si le sprite (4 paires x 16 lignes) touche une plateforme
* (même chevauchement horizontal que pour se poser : au moins 2 paires). Le test de hauteur,
* qui écarte presque toutes les plateformes, passe en premier.
BLOCKED STB     CY
        ADDB    #15
        STB     CYB             ; dernière ligne du sprite
        TFR     A,B
        ADDA    #2
        STA     CP2             ; paire + 2
        INCB
        STB     CP1             ; paire + 1
        LDX     #PLATS
        LDB     #NPLAT
BK1     LDA     CYB             ; Y + 15 >= dessus
        CMPA    2,X
        BLO     BK2
        LDA     2,X             ; dessus + 3 >= Y
        ADDA    #3
        CMPA    CY
        BLO     BK2
        LDA     CP2             ; paire + 2 >= début
        CMPA    ,X
        BLO     BK2
        LDA     CP1             ; paire + 1 < fin
        CMPA    1,X
        BHS     BK2
        ORCC    #1
        RTS
BK2     LEAX    3,X
        DECB
        BNE     BK1
        ANDCC   #$FE
        RTS

****************************************************************
* ennemis
ENNTICK LDB     NENN
        BEQ     EN9
        LDU     #ENTS+ESIZE
EN1     PSHS    B
        INC     12,U
        LDA     11,U
        CMPA    #T_ROBOT
        BNE     EN2
        JSR     E_ROBOT
        BRA     EN8
EN2     CMPA    #T_CHAUV
        BNE     EN3
        JSR     E_CHAUV
        BRA     EN8
EN3     CMPA    #T_BOULE
        BNE     EN4
        JSR     E_BOULE
        BRA     EN8
EN4     JSR     E_NUAGE
EN8     LEAU    ESIZE,U
        PULS    B
        DECB
        BNE     EN1
EN9     RTS

* robot : tombe, puis marche sur le sol ou les plateformes (demi-tour aux bords)
E_ROBOT LDA     ,U
        LDB     1,U
        JSR     SUPPORT
        BCS     ER2
        LDA     1,U             ; chute de 2 lignes par top
        ADDA    #2
        STA     NEWY
        LDA     ,U
        LDB     1,U
        JSR     LANDCHK
        BCS     ER1
        LDB     NEWY
ER1     STB     1,U
        RTS
ER2     LDA     12,U
        ANDA    SPDMASK
        BNE     ER9
        JMP     HMOVE
ER9     RTS

* chauve-souris : poursuit Toto sans traverser les plateformes ; si une plateforme
* l'empêche de monter ou descendre vers lui, elle la contourne par le côté (dP)
E_CHAUV LDA     12,U
        ANDA    SPDMASK
        BNE     EC2
        LDA     ,U              ; horizontal : vers Toto
        CMPA    ENTS
        BEQ     EC2
        BLO     EC1
        DECA
        BRA     EC1B
EC1     INCA
EC1B    PSHS    A
        LDB     1,U
        JSR     BLOCKED
        PULS    A
        BCS     EC2
        STA     ,U
EC2     LDA     12,U
        BITA    #1
        BNE     EC9
        LDA     1,U             ; vertical : vers Toto
        CMPA    ENTS+1
        BEQ     EC9
        BLO     EC3
        DECA
        BRA     EC4
EC3     INCA
EC4     TFR     A,B
        PSHS    B
        LDA     ,U
        JSR     BLOCKED
        PULS    B
        BCS     EC5
        STB     1,U
EC9     RTS
EC5     JMP     HMOVE           ; plateforme au-dessus/au-dessous : on la contourne

* boule : rebondit sur les bords et sur les plateformes
E_BOULE LDA     12,U
        BITA    #1
        BNE     EB1
        JSR     HMOVE
EB1     LDA     1,U
        ADDA    5,U
        CMPA    #YMIN
        BLO     EB2
        CMPA    #YMAX
        BHI     EB2
        TFR     A,B
        PSHS    B
        LDA     ,U
        JSR     BLOCKED
        PULS    B
        BCS     EB2
        STB     1,U
        RTS
EB2     NEG     5,U             ; rebond (bord ou plateforme)
        RTS

* nuage : dérive d'un bord à l'autre et descend vers Toto
E_NUAGE LDA     12,U
        BITA    #3
        BNE     EU1
        JSR     HMOVE
EU1     LDA     12,U
        ANDA    #3
        CMPA    #2
        BNE     EU9
        LDA     1,U
        CMPA    ENTS+1
        BEQ     EU9
        BLO     EU2
        DECA
        BRA     EU3
EU2     INCA
EU3     TFR     A,B
        PSHS    B
        LDA     ,U
        JSR     BLOCKED
        PULS    B
        BCS     EU9
        STB     1,U
EU9     RTS

* déplacement horizontal d'une paire (dP), demi-tour sur les bords et les plateformes
HMOVE   LDA     ,U
        ADDA    4,U
        CMPA    #PMIN
        BLT     HM1
        CMPA    #PMAX
        BGT     HM1
        PSHS    A
        LDB     1,U
        JSR     BLOCKED
        PULS    A
        BCS     HM1
        STA     ,U
        RTS
HM1     NEG     4,U             ; demi-tour (sans bouger ce top-ci)
        RTS

* apparition des ennemis : un toutes les 3 s, jusqu'à NMAXLV
SPAWNTICK
        DEC     SPT
        BNE     SW9
        LDA     #150
        STA     SPT
        LDA     NENN
        CMPA    NMAXLV
        BHS     SW9
        INCA
        STA     NENN
        LDB     #ESIZE
        MUL
        ADDD    #ENTS
        TFR     D,U
        LDA     NSPAWN          ; types en alternance : robot, chauve-souris, boule, nuage
        INC     NSPAWN
        ANDA    #3
        INCA
        STA     11,U
        CLR     12,U
        LDB     #8              ; côté opposé à Toto, en haut
        LDA     #1
        STA     4,U
        LDA     ENTS
        CMPA    #31
        BHS     SW1
        LDB     #52
        LDA     #-1
        STA     4,U
SW1     STB     ,U
        LDA     #YMIN+4
        STA     1,U
        LDA     #1
        STA     5,U
        LDA     11,U
        CMPA    #T_BOULE
        BNE     SW2
        LDA     #2
        STA     5,U
SW2     LDA     #$FF
        STA     2,U
        LDB     11,U            ; images du type
        DECB
        ASLB
        ASLB
        LDX     #TYPIMG
        ABX
        LDD     ,X
        STD     6,U
        LDD     2,X
        STD     8,U
SW9     RTS

****************************************************************
* collisions Toto / ennemis
COLLIDE TST     INVUL
        BEQ     CO1
        DEC     INVUL
        RTS
CO1     LDB     NENN
        BEQ     CO9
        LDU     #ENTS+ESIZE
CO2     LDA     ,U
        SUBA    ENTS
        BPL     CO3
        NEGA
CO3     CMPA    #3
        BHS     CO5
        LDA     1,U
        SUBA    ENTS+1
        BPL     CO4
        NEGA
CO4     CMPA    #12
        BLO     DEATH
CO5     LEAU    ESIZE,U
        DECB
        BNE     CO2
CO9     RTS

DEATH   LDA     #G_MORT
        STA     GSTATE
        LDA     #75
        STA     GTIMER
        JSR     TOTOIMG
        LDX     #SFX_MORT
        JMP     PLAYSFX

AFTERDEATH
        LDA     LIVES
        DECA
        STA     LIVES
        LDA     #1
        STA     DIRTY
        TST     LIVES
        BNE     AD1
        JSR     RECORDCHK       ; fin de partie
        LDA     #G_FIN
        STA     GSTATE
        LDA     #150
        STA     GTIMER
        LDA     #C_ROUGE
        STA     BORDER
        RTS
AD1     JSR     ERASEALL        ; on efface tout le monde et on repart
        CLR     NENN
        JSR     TOTORESET
        LDA     #100
        STA     INVUL
        LDA     #G_JEU
        STA     GSTATE
        CLR     BORDER
        RTS

RECORDCHK
        LDD     SCORE
        CMPD    RECORD
        BHI     RC1
        BLO     RC9
        LDA     SCORE+2
        CMPA    RECORD+2
        BLS     RC9
RC1     LDD     SCORE
        STD     RECORD
        LDA     SCORE+2
        STA     RECORD+2
RC9     RTS

****************************************************************
* bombes
BOMBCHK LDA     #NBOMB-1
        STA     BIDX
BC1     LDX     #BSTATE
        LDA     BIDX
        TST     A,X
        BEQ     BC3
        LDX     #BOMBS
        ASLA
        LEAX    A,X
        LDA     ,X              ; |paire - Toto| <= 2
        SUBA    ENTS
        BPL     BC1B
        NEGA
BC1B    CMPA    #2
        BHI     BC3
        LDA     1,X             ; |ligne - Toto| < 12
        SUBA    ENTS+1
        BPL     BC2
        NEGA
BC2     CMPA    #12
        BLO     TAKEBOMB
BC3     DEC     BIDX
        BPL     BC1
        RTS

TAKEBOMB
        LDX     #BSTATE
        LDA     BIDX
        CLR     A,X
        DEC     BLEFT
        LDA     #1
        STA     DIRTY
        JSR     BOMBHIDE
        LDA     BIDX
        CMPA    LIT
        BEQ     TB1
        LDX     #PTS100         ; bombe éteinte : 100
        JSR     ADDSCORE
        LDX     #SFX_BOMBE
        JSR     PLAYSFX
        BRA     TB5
TB1     LDX     #PTS200         ; bombe allumée : 200, la suivante s'allume
        JSR     ADDSCORE
        LDX     #SFX_ALLUMEE
        JSR     PLAYSFX
        TST     BLEFT
        BEQ     TB5
        LDA     LIT
TB2     INCA
        CMPA    #NBOMB
        BLO     TB3
        CLRA
TB3     LDX     #BSTATE
        TST     A,X
        BEQ     TB2
        STA     LIT
        STA     BIDX
        JSR     BOMBSHOW
TB5     TST     BLEFT           ; plus de bombes : niveau terminé
        BNE     TB9
        LDA     #G_BRAVO
        STA     GSTATE
        LDA     #60
        STA     GTIMER
        LDX     #SFX_NIVEAU
        JSR     PLAYSFX
TB9     RTS

* X = adresse de la bombe BIDX dans la copie du décor (banque A) ; A = paire, B = ligne
BOMBADR LDX     #BOMBS
        LDA     BIDX
        ASLA
        LEAX    A,X
        LDD     ,X
        STD     CP              ; CP = paire, CY = ligne
        LDA     CY              ; BUFA + (ligne-8)*29 + paire/2 - 2
        SUBA    #8
        LDB     #BUFROW
        MUL
        ADDD    #BUFA-2
        STD     TMPW
        LDB     CP
        LSRB
        CLRA
        ADDD    TMPW
        TFR     D,X
        RTS

* fond propre sous la bombe BIDX : copie du décor -> PATCH (2 x 16 lignes x 2 octets)
PATCHSAVE
        JSR     BOMBADR
        JSR     PATCHADR
        LDA     #16             ; (compteur en mémoire : LDD écrase B)
        STA     CNT
PS1     LDD     ,X
        STD     ,U
        LDD     BUFB-BUFA,X
        STD     32,U
        LEAX    BUFROW,X
        LEAU    2,U
        DEC     CNT
        BNE     PS1
        RTS
* U = PATCH + BIDX * 64
PATCHADR
        LDA     BIDX
        LDB     #64
        MUL
        ADDD    #PATCH
        TFR     D,U
        RTS

* efface la bombe BIDX : fond propre dans la copie du décor, puis à l'écran
BOMBHIDE
        JSR     BOMBADR
        JSR     PATCHADR
        LDA     #16
        STA     CNT
BH1     LDD     ,U
        STD     ,X
        LDD     32,U
        STD     BUFB-BUFA,X
        LEAX    BUFROW,X
        LEAU    2,U
        DEC     CNT
        BNE     BH1
        BRA     BOMBSCR

* dessine la bombe BIDX (allumée si BIDX = LIT) dans la copie du décor, puis à l'écran
BOMBSHOW
        JSR     BOMBADR
        LDY     #BUF_BOMBE
        LDA     BIDX
        CMPA    LIT
        BNE     BS1
        LDY     #BUF_BOMBE_AL
BS1     JSR     [,Y]            ; banque A (paires 0 et 2)
        JSR     [2,Y]
        LEAX    BUFB-BUFA,X     ; banque B (paires 1 et 3)
        JSR     [4,Y]
        JSR     [6,Y]
* recopie la zone de la bombe (copie du décor -> écran), puis répare Toto s'il y était
BOMBSCR LDA     CP
        LDB     CY
        JSR     ERASE
        LDU     #ENTS
        LDA     2,U
        CMPA    #$FF
        BEQ     BS9
        LDB     3,U
        LDY     6,U
        JMP     DRAW
BS9     RTS

* score += nombre BCD de 3 octets en X
ADDSCORE
        LDA     SCORE+2
        ADDA    2,X
        DAA
        STA     SCORE+2
        LDA     SCORE+1
        ADCA    1,X
        DAA
        STA     SCORE+1
        LDA     SCORE
        ADCA    ,X
        DAA
        STA     SCORE
        RTS
PTS10   FCB     $00,$00,$10
PTS100  FCB     $00,$01,$00
PTS200  FCB     $00,$02,$00

****************************************************************
* panneau : score, record, vies, niveau (chiffres 3x5 blancs sur noir)
SHOWSTATS
        TST     DIRTY
        BEQ     SS9
        CLR     DIRTY
        LDX     #SCORE
        LDA     #65
        LDB     #25
        JSR     SHOWBCD3
        LDX     #RECORD
        LDA     #65
        LDB     #63
        JSR     SHOWBCD3
        LDA     #69
        STA     TXP
        LDA     #103
        STA     TXY
        LDA     LIVES
        JSR     DIGIT
        LDA     #67
        STA     TXP
        LDA     #143
        STA     TXY
        LDA     LEVELB
        LSRA
        LSRA
        LSRA
        LSRA
        JSR     DIGIT
        LDA     #69
        STA     TXP
        LDA     LEVELB
        ANDA    #$0F
        JMP     DIGIT
SS9     RTS

* 3 octets BCD en X -> 6 chiffres en (paire A, ligne B)
SHOWBCD3
        STA     TXP
        STB     TXY
        LDB     #3
SB31    PSHS    B,X
        LDA     ,X
        LSRA
        LSRA
        LSRA
        LSRA
        JSR     DIGIT
        INC     TXP
        INC     TXP
        PULS    B,X
        PSHS    B,X
        LDA     ,X
        ANDA    #$0F
        JSR     DIGIT
        INC     TXP
        INC     TXP
        PULS    B,X
        LEAX    1,X
        DECB
        BNE     SB31
        RTS

* chiffre A en (paire TXP impaire, ligne TXY) : 5 lignes doublées ; le chiffre fait 3 pixels
* (paire TXP : pixels 0-1, paire TXP+1 : pixel 2 et un blanc)
DIGIT   LDB     #5
        MUL
        ADDD    #DIGITS
        STD     DGPTR
        LDA     TXP
        LDB     TXY
        JSR     ADDR            ; X = paire TXP ; TXP impaire : banque B puis banque A (X+1)
        PSHS    CC              ; (IRQ masquées ~250 cycles par banque)
        ORCC    #$50
        LDA     PRC             ; banque de la paire TXP (impaire : B)
        ANDA    #$FE
        STA     PRC
        LDU     DGPTR
        LDB     #5
DG1     LDA     ,U+
        LSRA                    ; bits 2-1 -> pixels 0-1
        ANDA    #3
        PSHS    X
        LDX     #DGLUT
        LDA     A,X
        PULS    X
        STA     ,X
        STA     40,X
        LEAX    80,X
        DECB
        BNE     DG1
        LEAX    -400+1,X        ; paire TXP+1 (banque A, octet suivant)
        PULS    CC              ; les IRQ en attente passent ici
        PSHS    CC
        ORCC    #$50
        LDA     PRC
        ORA     #1
        STA     PRC
        LDU     DGPTR
        LDB     #5
DG2     LDA     ,U+
        ANDA    #1              ; bit 0 -> pixel 2, puis un pixel de fond
        PSHS    X
        LDX     #DGLUT2
        LDA     A,X
        PULS    X
        STA     ,X
        STA     40,X
        LEAX    80,X
        DECB
        BNE     DG2
        PULS    CC,PC
DGLUT   FCB     $00,$08,$80,$88 ; (pixel 0, pixel 1) : fond noir / blanc
DGLUT2  FCB     $00,$80

****************************************************************
* son : IRQ timer du 6846 à 1000 Hz : bruitages (une voix carrée) ; horloge
SNDON   LDA     DACCR           ; port B du PIA jeux : bits 0-5 en sortie (CNA)
        ANDA    #$FB
        STA     DACCR
        LDA     #$3F
        STA     DAC
        LDA     DACCR
        ORA     #$04
        STA     DACCR
        CLR     DAC
        LDX     #SNDIRQ
        STX     TIMEPT
        LDA     STATUS
        ORA     #$20
        STA     STATUS
        LDA     #1
        STA     SNDFLAG
        JSR     SNDRATE
        LDA     #$42
        STA     TCR
        ANDCC   #$AF
        RTS
SNDRATE PSHS    CC
        ORCC    #$50
        LDD     #LATCH
        STD     TMSB
        LDA     #20
        STA     DIVREL
        STA     SNDDIV
        CLRA
        TST     SNDFLAG         ; S : bruitages oui / non
        BEQ     SR1
        LDA     #24
SR1     STA     VOL2
        PULS    CC,PC
SNDTOGGLE
        LDA     SNDFLAG
        EORA    #1
        STA     SNDFLAG
        JMP     SNDRATE

* bruitage X : incrément de départ, glissement, durée (tops)
PLAYSFX PSHS    CC
        ORCC    #$50
        LDD     ,X
        STD     SFXINC
        LDD     2,X
        STD     SFXSLIDE
        LDA     4,X
        STA     SFXCNT
        PULS    CC,PC
SFX_SAUT    FDB 6000,700
            FCB 10
SFX_BOMBE   FDB 20000,1500
            FCB 5
SFX_ALLUMEE FDB 16000,2500
            FCB 6
SFX_MORT    FDB 14000,-500
            FCB 25
SFX_NIVEAU  FDB 10000,800
            FCB 25

SNDIRQ  PSHS    D
        LDD     TIMEACC         ; horloge : +1000 cycles par IRQ
        ADDD    #LATCH+1
        STD     TIMEACC
        LDD     PH2             ; une voix carrée : les bruitages (pas de musique)
        ADDD    INC2
        STD     PH2
        LDB     VOL2
        TSTA
        BMI     SQ2
        CLRB
SQ2     STB     DAC
        DEC     SNDDIV
        BNE     SQ9
        LDA     DIVREL          ; top à 50 Hz
        STA     SNDDIV
        INC     TICK
        TST     SFXCNT          ; bruitage en cours : sa note glisse, puis silence
        BEQ     SQ9
        DEC     SFXCNT
        LDD     SFXINC
        STD     INC2
        ADDD    SFXSLIDE
        STD     SFXINC
        TST     SFXCNT
        BNE     SQ9
        LDD     #0
        STD     INC2
SQ9     PULS    D
        JMP     IRQEXIT

        INCLUDE "moteur.asm"
        INCLUDE "toboum_data.asm"
ENDCODE

        ORG     PATCH+NBOMB*64
VARS
NENN    RMB     1
ITER    RMB     1
TICK    RMB     1
LTICK   RMB     1
NTICK   RMB     1
LASTKEY RMB     1
IN_L    RMB     1
IN_R    RMB     1
IN_U    RMB     1
IN_D    RMB     1
JOYOK   RMB     1
TMPW    RMB     2
CNT     RMB     1
ULCNT   RMB     1
ULDIST  RMB     2
SNDFLAG RMB     1
SNDDIV  RMB     1
DIVREL  RMB     1
PH2     RMB     2
INC2    RMB     2
VOL2    RMB     1
SFXINC  RMB     2
SFXSLIDE RMB    2
SFXCNT  RMB     1
ENTS    RMB     ESIZE*(NMAX+1)
ORDER   RMB     NMAX+1
NACT    RMB     1
SI      RMB     1
SJ      RMB     1
SKEY    RMB     1
SKY     RMB     1
UPK     RMB     1
SPLITK  RMB     1
KK      RMB     1
MM      RMB     1
T2L     RMB     2
TIMEACC RMB     2
CLK0    RMB     2
CLKOK   RMB     1
MARGE   RMB     2
* jeu
GSTATE  RMB     1
GTIMER  RMB     1
SCORE   RMB     3
RECORD  RMB     3
LIVES   RMB     1
LEVELB  RMB     1               ; niveau en BCD (affichage)
LEVELN  RMB     1               ; niveau en binaire
NMAXLV  RMB     1
SPDMASK RMB     1
NSPAWN  RMB     1
SPT     RMB     1
INVUL   RMB     1
DIRTY   RMB     1
TYF     RMB     1
TVY     RMB     2
TVX     RMB     1
FACE    RMB     1
ONGND   RMB     1
GLIDE   RMB     1
JLATCH  RMB     1
HXC     RMB     1
OLDY    RMB     1
NEWY    RMB     1
CP      RMB     1               ; (CP puis CY : lus ensemble par LDD/STD)
CY      RMB     1
BIDX    RMB     1
BLEFT   RMB     1
LIT     RMB     1
BSTATE  RMB     NBOMB
PALPTR  RMB     2               ; palette courante
NEWPAL  RMB     2               ; palette du décor en préparation
PALRAM  RMB     32              ; palette d'un décor lu sur la disquette
LZPA    RMB     2               ; décor compressé : banque A
LZPB    RMB     2               ; banque B
DECN    RMB     1
LDTRK   RMB     1
LDSEC   RMB     1
TXP     RMB     1
TXY     RMB     1
CYB     RMB     1
CP1     RMB     1
CP2     RMB     1
DGPTR   RMB     2
VARSEND

        IFGT    ENDCODE-$E000
        ERROR   "le programme dépasse $DFFF"
        ENDC
        IFGT    VARSEND-$9E00
        ERROR   "les variables touchent la pile"
        ENDC
        END     START
