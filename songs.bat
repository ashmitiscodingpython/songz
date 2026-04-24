@echo off
set dire=%cd%
start "songzplayer" cmd /c "title songzplayer && cd /d %~dp0 && python songs.py "%dire%""
exit