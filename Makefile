ESP32SSDP_COMMIT := 503e9f86f005bf851691926095abcfc676a78b71

clean:
	rm -rf .esphome/build/oakesp/.piolibdeps .esphome/build/oakesp/.pioenvs
	
build:
	rm -rf .esphome/build/oakesp/.piolibdeps/oakesp/FauxmoESP
	rm -rf .esphome/build/oakesp/.piolibdeps/oakesp/ESP32SSDP
	uv run esphome compile oakesp.yaml
	uv run esphome upload --device 10.1.20.194 oakesp.yaml

patch-esp32ssdp:
	cd ESP32SSDP && git checkout $(ESP32SSDP_COMMIT)
	cd ESP32SSDP && git apply ../ESP32SSDP.patch