#!/usr/bin/bash

packageName="gghk-1.0.2-centos-7.6.tar.gz"
chmod u+x $HOME/gghc/GGHC.py
chmod u+x $HOME/gghs/agent.py
chmod u+x $HOME/bin/floatip.sh
chmod u+x $HOME/bin/gghc.sh

mv $HOME/bin/floatip.sh  $HOME/.

cd $HOME
tar cvf gghc.tar gghc conf bin license COPYRIGHT
tar cvf gghs.tar gghs license COPYRIGHT
tar zcvf $packageName  gghc.tar gghs.tar floatip.sh
rm -rf gghc.tar gghs.tar