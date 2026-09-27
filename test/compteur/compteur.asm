****************************************************************
* COMPTEUR : relevé des registres $E7E4-$E7E7 (compteur ligne-trame du crayon optique)
* à des instants connus au cycle près, pour savoir s'ils donnent la position du faisceau.
*   1. relevé large : dès le retour de trame (bit 7 de $E7E7 qui retombe), 24 mesures,
*      une toutes les 852 cycles (~13,3 lignes de 64 cycles) : une image entière ;
*   2. relevé fin : à la trame suivante, 7 000 cycles après, 16 mesures espacées de 33 et
*      38 cycles en alternance (~9 lignes en tout) : progression le long des lignes.
* Interruptions masquées pendant les mesures, puis affichage en hexadécimal :
*   nn E4E5 E6 E7   (n° de mesure, $E7E4:$E7E5, $E7E6, $E7E7)
* Lancer : RUN"COMPTEUR" (BASIC 128 sur TO9, BASIC 512 sur TO8/TO9+).
****************************************************************
PUTC    EQU     $E803
GATE4   EQU     $E7E4
GATE5   EQU     $E7E5
GATE6   EQU     $E7E6
GATE7   EQU     $E7E7
NLARGE  EQU     24
NFIN    EQU     16

        ORG     $A000
START   PSHS    CC,D,X,Y,U
        ORCC    #$50
        JSR     VBL
* 1. relevé large : 52 + 8 x 100 = 852 cycles par mesure
        LDU     #LARGE
        LDB     #NLARGE
L1      LDA     GATE4           ; 5 + 6
        STA     ,U+
        LDA     GATE5
        STA     ,U+
        LDA     GATE6
        STA     ,U+
        LDA     GATE7
        STA     ,U+
        LDX     #100            ; 3
L2      LEAX    -1,X            ; 5
        BNE     L2              ; 3
        DECB                    ; 2
        BNE     L1              ; 3
* 2. relevé fin, à la trame suivante : ~7 000 cycles après le retour de trame, 33 cycles par mesure
        JSR     VBL
        LDX     #875            ; 875 x 8 = 7 000 cycles
L3      LEAX    -1,X
        BNE     L3
        LDU     #FIN
        LDB     #NFIN
L4      LDA     GATE4           ; boucle déroulée par 2 : 2 mesures = 66 cycles
        STA     ,U+
        LDA     GATE5
        STA     ,U+
        LDA     GATE6
        STA     ,U+
        LDA     GATE4
        STA     ,U+
        LDA     GATE5
        STA     ,U+
        LDA     GATE6
        STA     ,U+
        SUBB    #2
        BNE     L4
        ANDCC   #$AF
* affichage
        LDX     #TXT1
        JSR     PRINT
        LDY     #LARGE
        CLR     NUM
        LDB     #NLARGE
A1      PSHS    B
        JSR     SAMPLE4
        PULS    B
        DECB
        PSHS    B
        BITB    #1              ; deux mesures par ligne
        BEQ     A2
        LDX     #SEP
        JSR     PRINT
        BRA     A3
A2      JSR     CRLF
A3      PULS    B
        TSTB
        BNE     A1
        LDX     #TXT2
        JSR     PRINT
        LDY     #FIN
        CLR     NUM
        LDB     #NFIN
F1      PSHS    B
        JSR     SAMPLE3
        PULS    B
        DECB
        PSHS    B
        BITB    #1
        BEQ     F2
        LDX     #SEP
        JSR     PRINT
        BRA     F3
F2      JSR     CRLF
F3      PULS    B
        TSTB
        BNE     F1
        PULS    CC,D,X,Y,U,PC

* attend le retour de trame : bit 7 de $E7E7 à 1 (image) puis à 0 (comme WAITVBL)
VBL     LDA     GATE7
        BPL     VBL
V2      LDA     GATE7
        BMI     V2
        RTS

* « nn E4E5 E6 E7 » (Y avance de 4)
SAMPLE4 LDA     NUM
        INC     NUM
        BSR     HEX2
        BSR     SPACE
        LDA     ,Y+
        BSR     HEX2
        LDA     ,Y+
        BSR     HEX2
        BSR     SPACE
        LDA     ,Y+
        BSR     HEX2
        BSR     SPACE
        LDA     ,Y+
        BRA     HEX2
* « nn E4E5 E6 » (Y avance de 3)
SAMPLE3 LDA     NUM
        INC     NUM
        BSR     HEX2
        BSR     SPACE
        LDA     ,Y+
        BSR     HEX2
        LDA     ,Y+
        BSR     HEX2
        BSR     SPACE
        LDA     ,Y+
        BRA     HEX2

HEX2    PSHS    A
        LSRA
        LSRA
        LSRA
        LSRA
        BSR     HEX1
        PULS    A
        ANDA    #$0F
HEX1    CMPA    #10
        BLO     H1
        ADDA    #'A-10
        BRA     H2
H1      ADDA    #'0
H2      TFR     A,B
        JMP     PUTC
SPACE   LDB     #32
        JMP     PUTC
CRLF    LDB     #13
        JSR     PUTC
        LDB     #10
        JMP     PUTC
PRINT   LDB     ,X+
        BEQ     P9
        PSHS    X
        JSR     PUTC
        PULS    X
        BRA     PRINT
P9      RTS

TXT1    FCB     12              ; efface l'écran
        FCC     "LARGE: 852 CYCLES"
        FCB     13,10,0
TXT2    FCC     "FIN: +7000, 33/38 CYCLES"
        FCB     13,10,0
SEP     FCC     "   "
        FCB     0
NUM     RMB     1
LARGE   RMB     NLARGE*4
FIN     RMB     NFIN*3

        END     START
