<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xupdate="http://www.xmldb.org/xupdate">

<!-- si se omite output encoding, se hereda del documento que procesamos -->
<xsl:output method="xml" version="1.0" indent="yes" omit-xml-declaration="yes"/>
  
<!-- identity template -->
<xsl:template match="@*|node()">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
</xsl:template>

<xsl:template match="/xml-patch">
    <xupdate:modifications version="legacy1">
        <xsl:apply-templates select="patch-node/*"/>
    </xupdate:modifications>
</xsl:template>

<xsl:template match="/xml-patch/patch-node/subnode[@action='noop']" />

<xsl:template match="/xml-patch/patch-node/subnode[@action='insert' and count(preceding-sibling::subnode[@action!='delete']) > 0]">
    <xupdate:insert-after>
        <xsl:attribute name="select">
            <xsl:value-of select="concat(../@select, '/', (preceding-sibling::subnode[@action!='delete'])[last()]/@select)" />
        </xsl:attribute>        
        <xsl:apply-templates select="node()"/>
    </xupdate:insert-after>
</xsl:template>

<xsl:template match="/xml-patch/patch-node/subnode[@action='insert' and count(preceding-sibling::subnode[@action!='delete']) = 0]">
    <xupdate:append-first>
        <xsl:attribute name="select">
            <xsl:value-of select="../@select" />
        </xsl:attribute>        
        <xsl:apply-templates select="node()"/>
    </xupdate:append-first>
</xsl:template>

<xsl:template match="/xml-patch/patch-node/update-text">
    <xupdate:update>
        <xsl:attribute name="select">
            <xsl:value-of select="concat(../@select,'/text()[1]')" />
        </xsl:attribute>        
        <xsl:value-of select="@new" />
    </xupdate:update>
</xsl:template>

<!-- TODO: Falta definir el formato para actualizar @atributos -->


<xsl:template match="/xml-patch/patch-node/subnode[@action='delete']">
    <xupdate:delete>
        <xsl:attribute name="select">
            <xsl:value-of select="concat(../@select, '/', @select)" />
        </xsl:attribute>        
    </xupdate:delete>
</xsl:template>



</xsl:stylesheet>
