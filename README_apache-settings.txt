1. ADD This to httpd-vhosts.conf 
#Start of: This is for slackel package finder Replace packagefinder.ddnsfree.com with your domain name
<Directory "/srv/httpd/htdocs/packagefinder/api">
    Options +ExecCGI
    AddHandler cgi-script .py
    Require all granted
</Directory>
#End of: This is for slackel package finder
================================================
#Full settings for virtual host
==================================================
# Virtual Hosts
#
# Required modules: mod_log_config

####
Listen 443
SSLCipherSuite HIGH:MEDIUM:!MD5:!RC4:!3DES
SSLProxyCipherSuite HIGH:MEDIUM:!MD5:!RC4:!3DES
SSLHonorCipherOrder on 
SSLProtocol all -SSLv3
SSLProxyProtocol all -SSLv3
SSLPassPhraseDialog  builtin
SSLSessionCache        "shmcb:/var/run/ssl_scache(512000)"
SSLSessionCacheTimeout  300
####

<VirtualHost *:80>
    ServerAdmin webmaster@packagefinder.ddnsfree.com
    DocumentRoot "/srv/httpd/htdocs/packagefinder"
    ServerName packagefinder.ddnsfree.com
    ErrorLog "/var/log/httpd/packagefinder.ddnsfree.com-error_log"
    CustomLog "/var/log/httpd/packagefinder.ddnsfree.com-access_log" common
    
	# to be able to use it for multiple domains. You'd use this snippet:
	Alias /.well-known/acme-challenge/ /var/www/dehydrated/
	<Directory /var/www/dehydrated/>
		Options None
		AllowOverride None
		Require all granted
	</Directory>
    
    RewriteEngine On
	RewriteCond %{HTTPS} off
	#RewriteRule (.*) https://%{HTTP_HOST}%{REQUEST_URI}
	RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]
</VirtualHost>

<VirtualHost *:443>
#   General setup for the virtual host
DocumentRoot "/srv/httpd/htdocs/packagefinder"
ServerName packagefinder.ddnsfree.com:443
ServerAdmin webmaster@packagefinder.ddnsfree.com
ErrorLog "/var/log/httpd/packagefinder.ddnsfree.com-error_log"
TransferLog "/var/log/httpd/packagefinder.ddnsfree.com-access_log"

# 1. NEW: Enable .htaccess for the entire site (Homepage)
<Directory "/srv/httpd/htdocs/packagefinder">
    Options Indexes FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>

#Start of: This is for slackel package finder
# 2. Υπάρχον: Ρύθμιση για το slackel package finder (API)
<Directory "/srv/httpd/htdocs/packagefinder/api">
    Options +ExecCGI
    AddHandler cgi-script .py
    AllowOverride All
    Require all granted
</Directory>
#End of: This is for slackel package finder

# We store the dehydrated info under /var/www/dehydrated and use an Apache 'Alias'
	# to be able to use it for multiple domains. You'd use this snippet:
	Alias /.well-known/acme-challenge/ /var/www/dehydrated/
	<Directory /var/www/dehydrated/>
		Options None
		AllowOverride None
		Require all granted
	</Directory>
	
SSLEngine on

SSLCertificateFile       /etc/dehydrated/certs-letsencrypt/packagefinder.ddnsfree.com/cert.pem
SSLCertificateKeyFile    /etc/dehydrated/certs-letsencrypt/packagefinder.ddnsfree.com/privkey.pem
SSLCertificateChainFile  /etc/dehydrated/certs-letsencrypt/packagefinder.ddnsfree.com/chain.pem

#SSLCACertificatePath "/etc/ssl/certs"
#SSLCACertificateFile "/etc/ssl/certs/ca.crt"
#SSLCARevocationPath "/etc/ssl/crl"
#SSLCARevocationFile "/etc/ssl/crl/ca.crl"
</VirtualHost>

2. on /etc/httpd.conf have to exist this

LoadModule log_config_module lib64/httpd/modules/mod_log_config.so
#For Salckel package finder
LoadModule proxy_uwsgi_module lib64/httpd/modules/mod_proxy_uwsgi.so
<IfModule !mpm_prefork_module>
	LoadModule cgid_module lib64/httpd/modules/mod_cgid.so
</IfModule>
<IfModule mpm_prefork_module>
	#LoadModule cgi_module lib64/httpd/modules/mod_cgi.so
</IfModule>
# Virtual hosts
Include /etc/httpd/extra/httpd-vhosts.conf
======
create .htaccess in packagefinder folder (add ip's like xx.xxx.xxx.x which forbitten
<RequireAll>
    Require all granted
    Require not ip xx.xxx.xxx.x
</RequireAll>
