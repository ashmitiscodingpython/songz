@echo off
set dire=%cd%
start "songzplayer" wt.exe /c "title songzplayer && cd /d %~dp0 && python -X importtime songs.py 2> importtime.txt \"%dire%\""
exit