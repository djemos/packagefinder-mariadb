1. ADD This to httpd-vhosts.conf 
#Start of: This is for slackel package finder
<Directory "/srv/httpd/htdocs/slackware-browser/api">
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
    ServerAdmin webmaster@slackel.ddns.net
    DocumentRoot "/srv/httpd/htdocs/slackware-browser"
    ServerName slackel.ddns.net
    ErrorLog "/var/log/httpd/slackel.ddns.net-error_log"
    CustomLog "/var/log/httpd/slackel.ddns.net-access_log" common
    
    <If "%{REQUEST_URI} !~ m#/\.well-known/acme-challenge/#">
        Redirect permanent / https://slackel.ddns.net/slackel/
    </If> 
    
    RewriteEngine On
	RewriteCond %{HTTPS} off
	RewriteRule (.*) https://%{HTTP_HOST}%{REQUEST_URI}
	#RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]
</VirtualHost>

<VirtualHost *:443>
#   General setup for the virtual host
DocumentRoot "/srv/httpd/htdocs/slackware-browser"
ServerName slackel.ddns.net:443
ServerAdmin webmaster@slackel.ddns.net
ErrorLog "/var/log/httpd/slackel.ddns.net-error_log"
TransferLog "/var/log/httpd/slackel.ddns.net-access_log"

#Start of: This is for slackel package finder
<Directory "/srv/httpd/htdocs/slackware-browser/api">
    Options +ExecCGI
    AddHandler cgi-script .py
    Require all granted
</Directory>
#End of: This is for slackel package finder

# We store the dehydrated info under /usr/local and use an Apache 'Alias'
	# to be able to use it for multiple domains. You'd use this snippet:
	Alias /.well-known/acme-challenge/ /var/www/dehydrated/
	<Directory /var/www/dehydrated/>
		Options None
		AllowOverride None
		Require all granted
	</Directory>
	
SSLEngine on

SSLCertificateFile       /etc/dehydrated/certs-letsencrypt/slackel.ddns.net/cert.pem
SSLCertificateKeyFile    /etc/dehydrated/certs-letsencrypt/slackel.ddns.net/privkey.pem
SSLCertificateChainFile  /etc/dehydrated/certs-letsencrypt/slackel.ddns.net/chain.pem

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
