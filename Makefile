FAUXMOESP_COMMIT := 1b8b91e362bc4c2f0891f1160c69f1e399346c02

clean:
	rm -rf .esphome/build/oakesp/.piolibdeps .esphome/build/oakesp/.pioenvs
	
build:
	uv run esphome compile oakesp.yaml
	uv run esphome upload --device 10.1.20.194 oakesp.yaml

sync-fauxmoesp:
	@if [ ! -d "fauxmoESP" ]; then \
		git clone https://github.com/vintlabs/fauxmoESP.git fauxmoESP; \
	fi
	cd fauxmoESP && git checkout $(FAUXMOESP_COMMIT)

apply-patch: sync-fauxmoesp
	cd fauxmoESP && git apply ../fauxmoESP.patch
	cp fauxmoESP/src/FauxmoESP.{h,cpp} components/fauxmoesp/

build-patch: sync-fauxmoesp
	cd fauxmoESP && git diff > ../fauxmoESP.patch