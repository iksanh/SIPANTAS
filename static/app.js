/* SIPANTAS - JavaScript sendiri, tanpa pustaka luar. */
(function () {
  "use strict";

  /* ---------------- tab ---------------- */
  /* Satu bilah tab per halaman. Peran ARIA dipasang di sini supaya penanda di
     web.py tetap ringkas, lengkap dengan panah kiri/kanan dan ingatan per
     halaman. Tab yang memuat sasaran #hash menang atas ingatan itu. */
  function pasangTab() {
    document.querySelectorAll('.tab[role="tablist"]').forEach(function (tab) {
      var tombol = Array.prototype.slice.call(tab.querySelectorAll("button[data-panel]"));
      var panel = tombol.map(function (b) { return document.getElementById(b.dataset.panel); });
      var kunci = "tab-" + (tab.dataset.tab || location.pathname);

      panel.forEach(function (p, i) {
        if (!p) return;
        p.setAttribute("role", "tabpanel");
        p.setAttribute("aria-labelledby", tombol[i].id);
        p.setAttribute("tabindex", "0");
      });

      function pilih(b, fokus) {
        tombol.forEach(function (x, i) {
          var aktif = x === b;
          x.classList.toggle("aktif", aktif);
          x.setAttribute("aria-selected", aktif ? "true" : "false");
          x.tabIndex = aktif ? 0 : -1;
          if (panel[i]) panel[i].classList.toggle("aktif", aktif);
        });
        if (fokus) b.focus();
        try { localStorage.setItem(kunci, b.dataset.panel); } catch (e) {}
      }

      tab.addEventListener("click", function (ev) {
        var b = ev.target.closest("button[data-panel]");
        if (b) pilih(b);
      });

      tab.addEventListener("keydown", function (ev) {
        var i = tombol.indexOf(document.activeElement);
        if (i < 0) return;
        var tujuan = { ArrowRight: i + 1, ArrowLeft: i - 1,
                       Home: 0, End: tombol.length - 1 }[ev.key];
        if (tujuan === undefined) return;
        ev.preventDefault();
        pilih(tombol[(tujuan + tombol.length) % tombol.length], true);
      });

      var awal = null;
      if (location.hash) {
        var sasaran = document.querySelector(location.hash);
        var induk = sasaran && sasaran.closest(".panel");
        if (induk) awal = tab.querySelector('button[data-panel="' + induk.id + '"]');
      }
      if (!awal && !tab.dataset.tahap) {
        /* Bilah langkah selalu mulai dari langkah satu: isian yang belum
           tersimpan hilang saat halaman dimuat ulang, jadi meneruskan ke
           tengah-tengah hanya membingungkan. */
        var simpan = null;
        try { simpan = localStorage.getItem(kunci); } catch (e) {}
        awal = simpan && tab.querySelector('button[data-panel="' + simpan + '"]');
      }
      pilih(awal || tombol[0]);
      if (tab.dataset.tahap) tandaiLangkah(tab);
    });
  }

  /* ---------------- menu samping ---------------- */
  /* Dua keadaan yang tak berkaitan:
       kuncup  - layar lebar, menu menyempit jadi ikon saja. Diingat.
       buka    - layar sempit, menu keluar sebagai laci di atas isi. Tidak
                 diingat: tiap halaman baru mestinya mulai tertutup.
     Keduanya kelas di <html> supaya CSS saja yang mengatur tampilannya. */
  function pasangMenu() {
    var akar = document.documentElement;
    var kuncup = document.getElementById("kuncup");
    var buka = document.getElementById("buka-nav");
    var tabir = document.getElementById("tabir");
    var samping = document.getElementById("samping");

    if (kuncup) {
      var labeli = function () {
        var ada = akar.classList.contains("menu-kuncup");
        var teks = ada ? "Lebarkan menu" : "Kuncupkan menu";
        kuncup.setAttribute("aria-label", teks);
        kuncup.title = teks;
      };
      labeli();
      kuncup.addEventListener("click", function () {
        var ada = akar.classList.toggle("menu-kuncup");
        try { localStorage.setItem("menu-kuncup", ada ? "1" : "0"); } catch (e) {}
        labeli();
      });
    }

    function laci(tampil) {
      akar.classList.toggle("menu-buka", tampil);
      if (buka) buka.setAttribute("aria-expanded", tampil ? "true" : "false");
      if (tabir) tabir.hidden = !tampil;
    }
    if (buka) buka.addEventListener("click", function () {
      laci(!akar.classList.contains("menu-buka"));
    });
    if (tabir) tabir.addEventListener("click", function () { laci(false); });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && akar.classList.contains("menu-buka")) laci(false);
    });
    /* Menekan tautan menu di layar sempit langsung menutup lacinya, jadi
       halaman berikutnya tidak tertutup laci yang masih terbuka. */
    if (samping) samping.addEventListener("click", function (ev) {
      if (ev.target.closest("a")) laci(false);
    });
    /* Bilah atas (layar sempit) diberi bayangan begitu halaman digulung. */
    var atas = document.querySelector(".atas");
    if (atas) {
      var gulung = function () { atas.classList.toggle("melayang", window.scrollY > 4); };
      gulung();
      window.addEventListener("scroll", gulung, { passive: true });
    }
  }

  /* ---------------- langkah pengisian berkas baru ---------------- */
  /* Bilah langkah memakai tombol tab yang sama; yang ditambahkan di sini cuma
     tombol maju/mundur dan penanda langkah yang sudah dilewati. */
  function tandaiLangkah(tab) {
    var tombol = Array.prototype.slice.call(tab.querySelectorAll("button[data-panel]"));
    var kini = tombol.findIndex(function (b) { return b.classList.contains("aktif"); });
    tombol.forEach(function (b, i) {
      b.classList.toggle("lewat", i < kini);
    });
  }

  function pasangLangkah() {
    var tab = document.querySelector(".tab.tahap");
    if (!tab) return;
    var tombol = Array.prototype.slice.call(tab.querySelectorAll("button[data-panel]"));

    function geser(arah) {
      var i = tombol.findIndex(function (b) { return b.classList.contains("aktif"); });
      var tujuan = tombol[i + arah];
      if (!tujuan) return;
      tujuan.click();
      tandaiLangkah(tab);
      /* Ke atas, supaya judul langkah yang baru benar-benar terlihat. */
      var atas = document.querySelector(".lengket-atas");
      window.scrollTo({ top: atas ? atas.offsetTop : 0, behavior: "smooth" });
    }

    document.addEventListener("click", function (ev) {
      if (ev.target.closest("[data-tahap-maju]")) { ev.preventDefault(); geser(1); }
      else if (ev.target.closest("[data-tahap-mundur]")) { ev.preventDefault(); geser(-1); }
    });
    tab.addEventListener("click", function () { setTimeout(function () { tandaiLangkah(tab); }, 0); });
  }

  /* ---------------- baris dinamis ---------------- */
  function nomori(wadah) {
    var i = 1;
    wadah.querySelectorAll(".baris").forEach(function (b) {
      var n = b.querySelector(".nomor") || b.querySelector(".no");
      if (n) n.textContent = i;
      var p = b.querySelector(".pegang");
      if (p) p.setAttribute("aria-label", "Pindahkan baris " + i);
      i++;
    });
  }

  function tetangga(baris, arah) {
    var x = baris[arah];
    while (x && !(x.classList && x.classList.contains("baris"))) x = x[arah];
    return x;
  }

  /* Ubah urutan DOM, lalu baris lain yang ikut tergeser meluncur dari tempat
     lamanya ke tempat barunya (FLIP) — jadi mata bisa mengikuti perpindahannya. */
  function denganAnimasi(wadah, kecuali, ubah) {
    var semua = [].slice.call(wadah.querySelectorAll(".baris"));
    var awal = semua.map(function (b) { return b.getBoundingClientRect().top; });
    ubah();
    semua.forEach(function (b, i) {
      if (b === kecuali) return;
      b.classList.remove("mendarat");
      b.style.transform = "";
      var d = awal[i] - b.getBoundingClientRect().top;
      if (!d) return;
      b.style.transform = "translateY(" + d + "px)";
      void b.offsetWidth;
      b.classList.add("mendarat");
      b.style.transform = "";
    });
  }

  /* Urutan berubah = formulir berubah: peringatan "belum disimpan" ikut tahu. */
  function urutanBerubah(wadah) {
    nomori(wadah);
    wadah.dispatchEvent(new Event("input", { bubbles: true }));
  }

  /* Seret-lepas lewat pegangan ⠿ di tiap baris. Memakai Pointer Events, jadi
     tetikus, layar sentuh, dan pena sama-sama jalan. Baris ikut kursor dan
     tetangganya menyingkir saat itu juga; urutan tersimpan waktu Simpan,
     sama seperti isian lainnya. Pegangan yang terfokus bisa digeser dengan
     ↑ / ↓ dari papan ketik. */
  function pasangSeret(wadah) {
    var aktif = null;

    function perbarui() {
      var a = aktif, b = a.baris;
      var dy = a.y + window.scrollY - a.y0;
      var tengah = b.offsetTop + b.offsetHeight / 2 + dy;
      var atas = tetangga(b, "previousElementSibling");
      var bawah = tetangga(b, "nextElementSibling");
      var tukar = null;
      if (atas && tengah < atas.offsetTop + atas.offsetHeight / 2)
        tukar = function () { wadah.insertBefore(b, atas); };
      else if (bawah && tengah > bawah.offsetTop + bawah.offsetHeight / 2)
        tukar = function () { wadah.insertBefore(b, bawah.nextSibling); };
      if (tukar) {
        var sebelum = b.offsetTop;
        denganAnimasi(wadah, b, tukar);
        a.y0 += b.offsetTop - sebelum;
        a.berubah = true;
        return perbarui();
      }
      /* Jangan sampai keluar jauh dari daftarnya. */
      var semua = wadah.querySelectorAll(".baris");
      var pertama = semua[0], akhir = semua[semua.length - 1];
      var min = pertama.offsetTop - b.offsetTop - 12;
      var maks = akhir.offsetTop + akhir.offsetHeight - b.offsetTop - b.offsetHeight + 12;
      b.style.transform = "translateY(" + Math.max(min, Math.min(maks, dy)) + "px)";
    }

    /* Kursor di dekat tepi layar: halaman ikut menggulir pelan-pelan. */
    function gulir() {
      if (!aktif) return;
      var y = aktif.y, tepiAtas = 90, tepiBawah = window.innerHeight - 70, v = 0;
      if (y < tepiAtas) v = -Math.min(18, (tepiAtas - y) / 4);
      else if (y > tepiBawah) v = Math.min(18, (y - tepiBawah) / 4);
      if (v && aktif.mulai) { window.scrollBy(0, v); perbarui(); }
      aktif.raf = requestAnimationFrame(gulir);
    }

    wadah.addEventListener("pointerdown", function (ev) {
      var p = ev.target.closest(".pegang");
      if (!p || aktif || (ev.pointerType === "mouse" && ev.button !== 0)) return;
      var baris = p.closest(".baris");
      if (!baris || baris.parentNode !== wadah) return;
      ev.preventDefault();
      try { p.setPointerCapture(ev.pointerId); } catch (e) {}
      baris.classList.remove("mendarat");
      baris.style.transform = "";
      aktif = { baris: baris, pegang: p, id: ev.pointerId, y: ev.clientY,
                y0: ev.clientY + window.scrollY, mulai: false, berubah: false };
      aktif.raf = requestAnimationFrame(gulir);
    });

    wadah.addEventListener("pointermove", function (ev) {
      if (!aktif || ev.pointerId !== aktif.id) return;
      aktif.y = ev.clientY;
      if (!aktif.mulai) {
        if (Math.abs(ev.clientY + window.scrollY - aktif.y0) < 4) return;
        aktif.mulai = true;
        aktif.baris.classList.add("diseret");
        wadah.classList.add("menyeret");
      }
      perbarui();
    });

    function selesai(ev) {
      if (!aktif || ev.pointerId !== aktif.id) return;
      var a = aktif;
      aktif = null;
      cancelAnimationFrame(a.raf);
      wadah.classList.remove("menyeret");
      a.baris.classList.remove("diseret");
      a.baris.classList.add("mendarat");
      a.baris.style.transform = "";
      if (a.berubah) urutanBerubah(wadah);
    }
    wadah.addEventListener("pointerup", selesai);
    wadah.addEventListener("pointercancel", selesai);

    wadah.addEventListener("keydown", function (ev) {
      var p = ev.target.closest && ev.target.closest(".pegang");
      if (!p || (ev.key !== "ArrowUp" && ev.key !== "ArrowDown")) return;
      var baris = p.closest(".baris");
      var lain = tetangga(baris, ev.key === "ArrowUp" ? "previousElementSibling" : "nextElementSibling");
      ev.preventDefault();
      if (!lain) return;
      denganAnimasi(wadah, null, function () {
        wadah.insertBefore(baris, ev.key === "ArrowUp" ? lain : lain.nextSibling);
      });
      p.focus();
      baris.classList.remove("dipindah");
      void baris.offsetWidth;
      baris.classList.add("dipindah");
      urutanBerubah(wadah);
    });
  }

  function pasangBarisDinamis() {
    document.querySelectorAll("[data-dinamis]").forEach(function (wadah) {
      var contoh = wadah.querySelector("template");

      wadah.addEventListener("click", function (ev) {
        var t = ev.target.closest("button");
        if (!t) return;
        var baris = t.closest(".baris");
        if (t.dataset.aksi === "hapus" && baris) {
          ev.preventDefault();
          baris.remove();
          urutanBerubah(wadah);
        }
      });
      pasangSeret(wadah);

      var tambah = document.querySelector('[data-tambah="' + wadah.dataset.dinamis + '"]');
      if (tambah && contoh) {
        tambah.addEventListener("click", function (ev) {
          ev.preventDefault();
          var isi = document.importNode(contoh.content, true);
          wadah.appendChild(isi);
          nomori(wadah);
          var baru = wadah.lastElementChild.querySelector("input,textarea,select");
          if (baru) baru.focus();
        });
      }
      nomori(wadah);
    });
  }

  /* ------------- desa mengikuti kecamatan ------------- */
  function pasangWilayah() {
    var kec = document.getElementById("f_kecamatan");
    var desa = document.getElementById("f_desa");
    if (!kec || !desa || !window.DAFTAR_DESA) return;

    function isi() {
      var terpilih = desa.dataset.terpilih || desa.value;
      var pilihan = window.DAFTAR_DESA.filter(function (d) {
        return !kec.value || String(d.kecamatan_id) === String(kec.value);
      });
      desa.innerHTML = '<option value="">- pilih desa/kelurahan -</option>';
      pilihan.forEach(function (d) {
        var o = document.createElement("option");
        o.value = d.id;
        o.textContent = d.jenis + " " + d.nama + (d.pejabat ? "  (" + d.pejabat + ")" : "");
        if (String(d.id) === String(terpilih)) o.selected = true;
        desa.appendChild(o);
      });
    }
    kec.addEventListener("change", function () { desa.dataset.terpilih = ""; isi(); });
    isi();
  }

  /* ------------- hitung selisih luas langsung ------------- */
  function pasangLuas() {
    var pbt = document.getElementById("f_luas_pbt");
    var surat = document.getElementById("f_luas_surat");
    var hasil = document.getElementById("f_selisih");
    if (!pbt || !surat || !hasil) return;
    function hitung() {
      var a = parseInt(pbt.value || "0", 10), b = parseInt(surat.value || "0", 10);
      if (!pbt.value || !surat.value) { hasil.value = ""; return; }
      var s = a - b;
      hasil.value = (s === 0 ? "tidak ada selisih"
        : (s > 0 ? "+" : "") + s.toLocaleString("id-ID") + " m²");
    }
    pbt.addEventListener("input", hitung);
    surat.addEventListener("input", hitung);
    hitung();
  }

  /* ------------- pencarian tabel di sisi klien ------------- */
  /* Kotak cari dan tab status menyaring tabel yang sama, jadi keduanya
     dihitung sekali dalam terapkan(). */
  function pasangSaring() {
    var kotak = document.getElementById("saring");
    var tapis = document.querySelector(".tab.tapis");
    if (!kotak && !tapis) return;
    var status = "";

    function terapkan() {
      var q = kotak ? kotak.value.toLowerCase().trim() : "";
      var n = 0;
      document.querySelectorAll("tbody tr[data-cari]").forEach(function (tr) {
        var cocok = (!q || tr.dataset.cari.indexOf(q) >= 0) &&
                    (!status || tr.dataset.status === status);
        tr.hidden = !cocok;
        if (cocok) n++;
      });
      var info = document.getElementById("jumlah-tampil");
      /* Satuannya ikut halaman: daftar berkas menghitung "berkas", daftar
         pradaftar menghitung "pradaftar". Halaman yang menyebutkannya lewat
         data-satuan; yang tidak, tetap "berkas" seperti dulu. */
      if (info) info.textContent = n + " " + (info.dataset.satuan || "berkas");
      var kosong = document.querySelector(".tak-cocok");
      if (kosong) kosong.hidden = n > 0;
    }

    if (kotak) kotak.addEventListener("input", terapkan);
    if (tapis) {
      tapis.addEventListener("click", function (ev) {
        var b = ev.target.closest("button[data-status]");
        if (!b) return;
        status = b.dataset.status;
        tapis.querySelectorAll("button").forEach(function (x) {
          x.classList.toggle("aktif", x === b);
          x.setAttribute("aria-pressed", x === b ? "true" : "false");
        });
        try { sessionStorage.setItem("tapis-status", status); } catch (e) {}
        terapkan();
      });
      var simpan = "";
      try { simpan = sessionStorage.getItem("tapis-status") || ""; } catch (e) {}
      var awal = tapis.querySelector('button[data-status="' + simpan + '"]') ||
                 tapis.querySelector("button");
      if (awal) awal.click();
    }
    terapkan();
  }

  /* ------------- saringan daftar berkas (sisi server) ------------- */
  /* Dropdown langsung mengirim formulirnya begitu diganti — tidak perlu
     menekan tombol lagi. Isian kosong dimatikan sebelum dikirim supaya
     alamatnya tidak penuh "?hak=&status=&kegiatan=". Pilihan "per halaman"
     ada di bawah tabel tapi ikut formulir ini lewat atribut form=. */
  function pasangSaringanServer() {
    var form = document.querySelector("form[data-saring-otomatis]");
    if (!form) return;
    form.addEventListener("submit", function () {
      Array.prototype.forEach.call(form.elements, function (el) {
        if (el.name && !el.value) el.disabled = true;
      });
      form.classList.add("memuat");
    });
    /* Kembali lewat tombol Back memulihkan halaman dari singgahan beserta
       isian yang tadi dimatikan; hidupkan lagi. */
    window.addEventListener("pageshow", function () {
      Array.prototype.forEach.call(form.elements, function (el) { el.disabled = false; });
      form.classList.remove("memuat");
    });
    document.addEventListener("change", function (ev) {
      var el = ev.target;
      if (el.tagName === "SELECT" && el.form === form) {
        if (form.requestSubmit) form.requestSubmit(); else form.submit();
      }
    });
    /* Esc di kotak cari yang terisi: kosongkan lalu cari ulang. */
    var cari = form.querySelector('input[type="search"]');
    if (cari) cari.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && cari.defaultValue) {
        cari.value = "";
        if (form.requestSubmit) form.requestSubmit(); else form.submit();
      }
    });
  }

  /* ------------- Ctrl+S menyimpan formulir ------------- */
  /* Hanya pada formulir bertanda data-simpan-pintas (berkas & pradaftar yang
     boleh diubah). Kirimnya lewat requestSubmit(tombol Simpan), jadi sama
     persis dengan mengklik tombolnya: validasi peramban ikut jalan dan
     nilai tombolnya ikut terkirim. */
  function pasangSimpanPintas() {
    var form = document.querySelector("form[data-simpan-pintas]");
    if (!form) return;
    var mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
    if (mac) document.querySelectorAll("kbd.pintas").forEach(function (k) {
      k.textContent = "⌘S";
      if (k.parentNode.title) k.parentNode.title = "Simpan (⌘S)";
    });
    var terkirim = false;

    form.addEventListener("submit", function (ev) {
      terkirim = true;
      var t = ev.submitter ||
              document.querySelector('button.utama[type="submit"][form="' + form.id + '"]');
      if (t) t.classList.add("sibuk");
    });
    window.addEventListener("pageshow", function () {
      terkirim = false;
      document.querySelectorAll(".btn.sibuk").forEach(function (b) { b.classList.remove("sibuk"); });
    });

    /* Isian tak sah yang tersembunyi di tab lain membuat peramban diam saja;
       bukakan tabnya supaya pesan validasinya kelihatan. */
    form.addEventListener("invalid", function (ev) {
      var panel = ev.target.closest(".panel");
      var tab = panel && document.getElementById("t-" + panel.id);
      if (tab && !panel.classList.contains("aktif")) tab.click();
    }, true);

    document.addEventListener("keydown", function (ev) {
      if (!(ev.ctrlKey || ev.metaKey) || ev.altKey || ev.shiftKey) return;
      if ((ev.key || "").toLowerCase() !== "s") return;
      ev.preventDefault();              /* jangan buka dialog "Simpan halaman" */
      if (terkirim || ev.repeat) return;
      var tombol = document.querySelector(
        'button.utama[type="submit"][form="' + form.id + '"]');
      if (form.requestSubmit) form.requestSubmit(tombol || undefined);
      else form.submit();
    });
  }

  /* ------------- konfirmasi tindakan ------------- */
  /* Didengarkan di tingkat dokumen supaya tombol pada potongan yang baru
     diambil (kartu lipat) ikut tertangani tanpa dipasangi ulang. */
  function pasangKonfirmasi() {
    document.addEventListener("click", function (ev) {
      var el = ev.target.closest("[data-konfirmasi]");
      if (el && !window.confirm(el.dataset.konfirmasi)) ev.preventDefault();
    });
  }

  /* ------------- kartu lipat, isinya diambil saat dibuka ------------- */
  var KUNCI_LIPAT = "lipat-terbuka";

  function ingatan() {
    try { return JSON.parse(localStorage.getItem(KUNCI_LIPAT) || "[]"); } catch (e) { return []; }
  }

  function ingat(id, buka) {
    var daftar = ingatan().filter(function (x) { return x !== id; });
    if (buka) daftar.push(id);
    try { localStorage.setItem(KUNCI_LIPAT, JSON.stringify(daftar.slice(-12))); } catch (e) {}
  }

  /* Isi kartu diambil sekali saja, saat kartunya pertama kali dibuka. */
  function muatIsi(kartu) {
    if (!kartu || kartu.dataset.terisi === "1") return;
    var kepala = kartu.querySelector(".lipat-kepala");
    var isi = kartu.querySelector(".lipat-isi");
    var alamat = kepala && kepala.getAttribute("data-muat");
    if (!alamat) return;
    kartu.dataset.terisi = "1";
    isi.innerHTML = '<div class="lipat-tunggu"><span class="putar"></span>Memuat…</div>';
    fetch(alamat, { credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) throw new Error("sesi");
        /* Tanpa penanda ini yang diterima bukan potongan kartu — jangan disuntikkan. */
        if (!r.ok || !r.headers.get("X-Potongan")) throw new Error(r.status);
        return r.text();
      })
      .then(function (teks) { isi.innerHTML = teks; })
      .catch(function (galat) {
        kartu.dataset.terisi = "";
        isi.innerHTML = galat && galat.message === "sesi"
          ? '<div class="lipat-galat"><span>Sesi sudah habis.</span>' +
            '<a class="btn kecil" href="/masuk">Masuk lagi</a></div>'
          : '<div class="lipat-galat"><span>Isi bagian ini gagal diambil.</span>' +
            '<button type="button" class="btn kecil" data-ulang>Coba lagi</button></div>';
      });
  }

  function setelLipat(kartu, buka, simpan) {
    var kepala = kartu.querySelector(".lipat-kepala");
    var isi = kartu.querySelector(".lipat-isi");
    kartu.classList.toggle("terbuka", buka);
    kepala.setAttribute("aria-expanded", buka ? "true" : "false");
    isi.hidden = !buka;
    if (simpan !== false) ingat(kartu.id, buka);
    if (buka) muatIsi(kartu);
  }

  function pasangLipat() {
    var semua = document.querySelectorAll(".lipat");
    if (!semua.length) return;

    document.addEventListener("click", function (ev) {
      if (ev.button || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
      var ulang = ev.target.closest("[data-ulang]");
      if (ulang) { muatIsi(ulang.closest(".lipat")); return; }
      var kepala = ev.target.closest(".lipat-kepala");
      if (!kepala) return;
      ev.preventDefault();
      var kartu = kepala.closest(".lipat");
      setelLipat(kartu, !kartu.classList.contains("terbuka"));
    });

    /* Yang sudah dirakit server dalam keadaan terbuka tak perlu diambil ulang. */
    semua.forEach(function (kartu) {
      if (kartu.classList.contains("terbuka")) {
        kartu.dataset.terisi = "1";
        ingat(kartu.id, true);
      }
    });

    /* Buka lagi bagian yang terakhir dipakai petugas. */
    ingatan().forEach(function (id) {
      var kartu = document.getElementById(id);
      if (kartu && kartu.classList.contains("lipat") && !kartu.classList.contains("terbuka"))
        setelLipat(kartu, true, false);
    });

    var sasaran = location.hash && document.querySelector(location.hash);
    if (sasaran && sasaran.classList && sasaran.classList.contains("lipat")) {
      setelLipat(sasaran, true);
      sasaran.scrollIntoView();
    }
  }

  /* ------------- saring isi satu kartu ------------- */
  /* Kotak cari dan saringan keadaan (.tapis-lipat) menunjuk wadah yang sama
     lewat id-nya; baris tampil bila cocok dengan keduanya. Keduanya
     didengarkan di tingkat dokumen karena isi kartu baru datang belakangan. */
  function saringWadah(id) {
    var wadah = document.getElementById(id);
    if (!wadah) return;
    var kotak = document.querySelector('input[data-saring="' + id + '"]');
    var tombol = document.querySelector('.tapis-lipat[data-tapis="' + id + '"] button.aktif');
    var q = kotak ? kotak.value.toLowerCase().trim() : "";
    var status = tombol ? tombol.dataset.status : "", n = 0;
    wadah.querySelectorAll("[data-cari]").forEach(function (el) {
      var cocok = (!q || el.dataset.cari.indexOf(q) >= 0) &&
                  (!status || el.dataset.status === status);
      el.hidden = !cocok;
      if (cocok) n++;
    });
    var info = kotak && kotak.parentNode.querySelector("[data-jumlah]");
    if (info) info.textContent = n + " " + info.dataset.jumlah;
    var kosong = (wadah.parentNode || wadah).querySelector(".tak-cocok");
    if (kosong) kosong.hidden = n > 0;
  }

  function pasangSaringLipat() {
    document.addEventListener("input", function (ev) {
      var kotak = ev.target.closest("input[data-saring]");
      if (kotak) saringWadah(kotak.dataset.saring);
    });
    document.addEventListener("click", function (ev) {
      var b = ev.target.closest(".tapis-lipat button[data-status]");
      if (b) {
        var grup = b.parentNode;
        grup.querySelectorAll("button").forEach(function (x) {
          x.classList.toggle("aktif", x === b);
          x.setAttribute("aria-pressed", x === b ? "true" : "false");
        });
        saringWadah(grup.dataset.tapis);
        return;
      }
      /* isi klausa yang dipotong tiga baris */
      var bentang = ev.target.closest("[data-bentang]");
      if (bentang) {
        var isi = bentang.previousElementSibling;
        var buka = isi.classList.toggle("bentang");
        bentang.textContent = buka ? "Ringkas" : "Selengkapnya";
      }
    });
  }

  /* ------------- foto yang dipilih tapi belum disimpan ------------- */
  function pasangPratinjauFoto() {
    document.querySelectorAll("input[data-pratinjau-foto]").forEach(function (masukan) {
      var wadah = document.getElementById(masukan.dataset.pratinjauFoto);
      if (!wadah) return;
      var alamat = [];
      masukan.addEventListener("change", function () {
        alamat.forEach(function (u) { URL.revokeObjectURL(u); });
        alamat = [];
        wadah.textContent = "";
        Array.prototype.forEach.call(masukan.files || [], function (berkas) {
          var fig = document.createElement("figure");
          var img = document.createElement("img");
          var u = URL.createObjectURL(berkas);
          alamat.push(u);
          img.src = u;
          img.alt = "";
          var cap = document.createElement("figcaption");
          cap.textContent = berkas.name;
          fig.appendChild(img);
          fig.appendChild(cap);
          wadah.appendChild(fig);
        });
        if (masukan.files && masukan.files.length) {
          var info = document.createElement("div");
          info.className = "petunjuk";
          info.style.flexBasis = "100%";
          info.textContent = masukan.files.length + " foto siap diunggah — tekan Simpan.";
          wadah.appendChild(info);
        }
      });
    });
  }

  /* ---------- rincian Akta Ikrar Wakaf & Pengesahan Nazhir ---------- */
  /* Pratinjau frasa Menimbang SK huruf b dan c. Susunannya harus sama dengan
     frasa_akta_ikrar / frasa_pengesahan_nazhir di konteks.py. */
  var BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
               "Agustus", "September", "Oktober", "November", "Desember"];
  var NAMA_AKTA = {AIW: "Akta Ikrar Wakaf", APAIW: "Akta Pengganti Akta Ikrar Wakaf"};

  function tanggalPanjang(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    return m ? m[3] + " " + BULAN[+m[2] - 1] + " " + m[1] : "";
  }

  function pasangRincianBaku() {
    var blok = {};
    document.querySelectorAll("[data-rincian-baku]").forEach(function (b) {
      blok[b.dataset.rincianBaku] = b;
    });
    if (!Object.keys(blok).length) return;

    function nilai(b, kolom) {
      var el = b.querySelector('[data-rincian="' + kolom + '"]');
      return el ? el.value.trim() : "";
    }
    function gabung(daftar) { return daftar.filter(Boolean).join(" "); }
    function oleh(b, akta) {
      var nama = nilai(b, "pejabat"), wil = nilai(b, "wilayah_pejabat");
      var jabatan = "Pejabat Pembuat " + akta + (wil ? " " + wil : "");
      return nama ? nama + " selaku " + jabatan : jabatan;
    }
    function frasa(kategori, b) {
      var ada = ["nomor", "tanggal", "pejabat", "wilayah_pejabat"].some(function (k) {
        return nilai(b, k);
      });
      if (!ada) return "";
      var tgl = tanggalPanjang(nilai(b, "tanggal")), nomor = nilai(b, "nomor");
      if (kategori === "akta_ikrar") {
        var akta = NAMA_AKTA[nilai(b, "jenis")] || NAMA_AKTA.AIW;
        return gabung([akta, tgl && "tanggal " + tgl, nomor && "Nomor " + nomor,
                       "yang dibuat oleh " + oleh(b, akta)]);
      }
      return gabung(["oleh " + oleh(b, "Akta Ikrar Wakaf"), tgl && "tanggal " + tgl,
                     nomor && "Nomor " + nomor]);
    }
    function segarkan(kategori) {
      var b = blok[kategori], sasaran = b && b.querySelector("[data-frasa]");
      if (!sasaran) return;
      var f = frasa(kategori, b);
      if (f) sasaran.textContent = f;           // tanpa rincian: biarkan teks dari server
      var ur = b.querySelector("textarea");
      if (ur && f) {
        ur.placeholder = kategori === "akta_ikrar" ? f
          : "Surat Pengesahan Nazhir yang disahkan " + f;
      }
    }

    Object.keys(blok).forEach(function (kategori) {
      blok[kategori].addEventListener("input", function () { segarkan(kategori); });
      blok[kategori].addEventListener("change", function () { segarkan(kategori); });
    });

    var tombol = document.querySelector("[data-salin-ppaiw]");
    if (tombol && blok.akta_ikrar && blok.pengesahan_nazhir) {
      tombol.addEventListener("click", function () {
        ["pejabat", "wilayah_pejabat"].forEach(function (k) {
          var dari = blok.akta_ikrar.querySelector('[data-rincian="' + k + '"]');
          var ke = blok.pengesahan_nazhir.querySelector('[data-rincian="' + k + '"]');
          if (dari && ke && dari.value.trim()) ke.value = dari.value.trim();
        });
        segarkan("pengesahan_nazhir");
      });
    }
  }

  /* ------------- tombol Cetak pada halaman pratinjau ------------- */
  function pasangCetak() {
    var tombol = document.querySelector("[data-cetak]");
    if (!tombol) return;
    tombol.addEventListener("click", function () {
      var bingkai = document.getElementById(tombol.dataset.cetak);
      /* Peramban modern bisa mencetak PDF di dalam iframe sealamat. Kalau
         penampil PDF-nya menolak - beberapa versi Firefox dan Safari begitu -
         PDF-nya dibuka di tab sendiri supaya penampil bawaan peramban yang
         menyediakan tombol cetaknya. */
      try {
        if (bingkai && bingkai.contentWindow) {
          bingkai.contentWindow.focus();
          bingkai.contentWindow.print();
          return;
        }
      } catch (e) { /* lintas-asal atau penampil menolak: jatuh ke bawah */ }
      window.open(tombol.dataset.pdf, "_blank", "noopener");
    });
  }

  /* ------------- daftar kelengkapan pradaftar ------------- */
  /* Keadaan tiap butir dihitung ulang di sini begitu pilihannya diganti,
     supaya petugas loket langsung tahu apa yang masih kurang tanpa menyimpan
     dulu. Aturannya CERMIN pradaftar._nilai, _kurang, _koreksi, dan progres
     di sisi server — kalau salah satunya diubah, yang lain ikut diubah.
     Keputusan yang mengikat (terima, cetak) tetap hitungan server. */
  var ADA = 1, TIDAK_BERLAKU = 2, KOREKSI = 3;

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function pohonPeriksa(akar) {
    var simpul = {}, daftar = [], puncak = [];
    akar.querySelectorAll(".periksa-baris[data-butir]").forEach(function (el) {
      var n = { id: el.dataset.butir, el: el, induk: el.dataset.induk || "",
                sifat: el.dataset.sifat, wajib: el.dataset.wajib === "1",
                berlaku: el.dataset.berlaku === "1", label: el.dataset.label,
                anak: [] };
      simpul[n.id] = n;
      daftar.push(n);
      var ind = simpul[n.induk];
      n.indukN = ind || null;
      (ind ? ind.anak : puncak).push(n);
    });
    return { daftar: daftar, puncak: puncak };
  }

  function bacaJawab(n) {
    var r = n.el.querySelector('input[type="radio"]:checked');
    n.dijawab = !!r;
    n.ada = r ? parseInt(r.value, 10) : 0;
    var c = n.el.querySelector(".periksa-koreksi input");
    n.catatan = c ? c.value.trim() : "";
  }

  function nilai(n) {                             /* = pradaftar._nilai */
    n.anak.forEach(nilai);
    if (!n.berlaku || n.ada === TIDAK_BERLAKU) return (n.status = "lewat");
    if (!n.anak.length) {
      if (n.ada === ADA) n.status = "ada";
      else if (n.ada === KOREKSI) n.status = "koreksi";
      else if (n.sifat === "alternatif") n.status = "lewat";
      else n.status = n.wajib ? "kurang" : "lewat";
      return n.status;
    }
    var berlaku = n.anak.filter(function (a) { return a.berlaku; });
    var pilihan = berlaku.filter(function (a) { return a.sifat === "alternatif"; });
    var tetap = berlaku.filter(function (a) { return a.sifat !== "alternatif"; });
    var cukup = !pilihan.length || pilihan.some(function (a) { return a.status === "ada"; });
    var tetapOk = tetap.every(function (a) { return a.status !== "kurang"; });
    var koreksi = berlaku.some(function (a) { return a.status === "koreksi"; });
    if (!tetapOk) n.status = n.wajib ? "kurang" : "lewat";
    else if (!cukup) n.status = koreksi ? "koreksi" : (n.wajib ? "kurang" : "lewat");
    else n.status = koreksi ? "koreksi" : "ada";
    return n.status;
  }

  function kurangDari(puncak) {                   /* = pradaftar._kurang */
    var hasil = [];
    (function telusur(simpul) {
      simpul.forEach(function (n) {
        if (n.status !== "kurang") return;
        if (n.anak.length && n.anak.some(function (a) {
              return a.sifat === "alternatif" && a.berlaku; })) hasil.push(n);
        else if (n.anak.length) telusur(n.anak);
        else hasil.push(n);
      });
    })(puncak);
    return hasil;
  }

  function koreksiDari(puncak) {                  /* = pradaftar._koreksi */
    var hasil = [];
    (function telusur(simpul) {
      simpul.forEach(function (n) {
        if (n.anak.length) telusur(n.anak);
        else if (n.status === "koreksi") hasil.push(n);
      });
    })(puncak);
    return hasil;
  }

  function bisaCentang(n) { return n.berlaku && n.sifat !== "judul"; }

  function progresDari(daftar) {                  /* = pradaftar.progres */
    var satuan = {}, urut = [];
    daftar.forEach(function (n) {
      if (!bisaCentang(n)) return;
      var k = n.sifat === "alternatif" ? "g" + n.induk : "b" + n.id;
      if (!satuan[k]) { satuan[k] = []; urut.push(k); }
      satuan[k].push(n);
    });
    var sudah = 0;
    urut.forEach(function (k) {
      var isi = satuan[k];
      var ok = k.charAt(0) === "b" ? isi[0].dijawab :
        isi.some(function (x) { return x.dijawab && (x.ada === ADA || x.ada === KOREKSI); }) ||
        isi.every(function (x) { return x.dijawab; });
      if (ok) sudah++;
    });
    return { sudah: sudah, semua: urut.length, satuan: satuan, urut: urut };
  }

  function belumDiperiksa(n) {                    /* = web._belum_diperiksa */
    if (n.anak.length) return !n.anak.some(function (a) { return a.berlaku && a.dijawab; });
    return !n.dijawab;
  }

  var CAP_GRUP = {                                /* = web._cap_grup */
    ada: '<span class="cap hijau">terpenuhi</span>',
    kurang: '<span class="cap merah">belum</span>',
    koreksi: '<span class="cap kuning">perlu koreksi</span>'
  };

  function ringkasPeriksa(kurang, koreksi) {      /* = web._ringkas_periksa */
    function tautan(n, tambahan) {
      return '<li><a href="#butir-' + n.id + '" data-lompat="' + n.id + '">' +
             esc(n.label) + "</a>" + (tambahan || "") + "</li>";
    }
    var h = "";
    if (kurang.length) h += '<div class="pesan galat"><div class="teks"><b>' + kurang.length +
      ' belum lengkap.</b> Berkas belum bisa diterima di loket.<ul class="rapat">' +
      kurang.map(function (n) {
        return tautan(n, belumDiperiksa(n) ? ' <span class="petunjuk">· belum diperiksa</span>' : "");
      }).join("") + "</ul></div></div>";
    if (koreksi.length) h += '<div class="pesan ingat"><div class="teks"><b>' + koreksi.length +
      ' perlu koreksi.</b> Suratnya ada, tetapi harus diperbaiki pemohon dulu.<ul class="rapat">' +
      koreksi.map(function (n) {
        return tautan(n, n.catatan ? " — <i>" + esc(n.catatan) + "</i>"
                                   : " — <i>catatannya belum diisi</i>");
      }).join("") + "</ul></div></div>";
    return h || '<div class="pesan baik"><div class="teks"><b>Kelengkapan terpenuhi.</b> ' +
                'Berkas siap diterima di loket.</div></div>';
  }

  function pasangPeriksa() {
    var akar = document.querySelector("[data-periksa]");
    if (!akar) return;
    var pohon = pohonPeriksa(akar);
    if (!pohon.daftar.length) return;
    var tapis = "", hasil = null;
    var kosong = akar.querySelector("[data-periksa-kosong]");
    var ringkasTunda = null;

    function hitung(ringkasSegera) {
      pohon.daftar.forEach(bacaJawab);
      pohon.puncak.forEach(nilai);
      var kurang = kurangDari(pohon.puncak), koreksi = koreksiDari(pohon.puncak);
      var p = progresDari(pohon.daftar);
      hasil = { kurang: kurang, koreksi: koreksi, p: p };

      pohon.daftar.forEach(function (n) {
        var el = n.el;
        el.classList.toggle("kurang", n.status === "kurang");
        el.classList.toggle("koreksi", n.status === "koreksi");
        el.classList.toggle("belum", bisaCentang(n) && !n.dijawab);
        var cap = el.querySelector("[data-cap]");
        if (cap && n.berlaku) cap.innerHTML = CAP_GRUP[n.status] || "";
        /* Catatan koreksi wajib diisi: surat pengembalian tanpa catatan tidak
           memberi tahu pemohon apa yang harus diperbaiki. */
        var c = el.querySelector(".periksa-koreksi input");
        if (c && !c.disabled) c.required = n.ada === KOREKSI;
      });

      var persen = p.semua ? Math.round(100 * p.sudah / p.semua) : 100;
      akar.querySelectorAll("[data-progres]").forEach(function (b) {
        b.querySelector("[data-progres-sudah]").textContent = p.sudah;
        b.querySelector("[data-progres-semua]").textContent = p.semua;
        b.querySelector("[data-progres-persen]").textContent = persen + "%";
        var bar = b.querySelector(".progres");
        bar.setAttribute("aria-valuenow", p.sudah);
        bar.firstElementChild.style.width = persen + "%";
        b.classList.toggle("penuh", p.sudah === p.semua);
      });
      var n = function (s, v) {
        akar.querySelectorAll('[data-hitung="' + s + '"]').forEach(function (x) {
          x.textContent = v;
        });
      };
      n("belum", p.semua - p.sudah);
      n("masalah", kurang.length + koreksi.length);

      /* Ringkasan ditunda sebentar selagi catatan diketik, supaya daftar
         tautannya tidak berkedip tiap huruf. */
      clearTimeout(ringkasTunda);
      var tulis = function () {
        akar.querySelectorAll("[data-periksa-ringkas]").forEach(function (r) {
          r.innerHTML = ringkasPeriksa(kurang, koreksi);
        });
      };
      if (ringkasSegera) tulis(); else ringkasTunda = setTimeout(tulis, 300);

      var lencana = document.querySelector("[data-lencana-periksa]");
      if (lencana) {
        var sisa = kurang.length + koreksi.length;
        lencana.textContent = sisa ? sisa : "✓";
        lencana.classList.toggle("merah", !!sisa);
        lencana.classList.toggle("hijau", !sisa);
      }
      saring();
    }

    function tampilMenurut(n) {
      if (tapis === "belum") return bisaCentang(n) && !n.dijawab &&
        !(n.sifat === "alternatif" && selesaiKelompok(n));
      if (tapis === "masalah") {
        if (n.status === "kurang" || n.status === "koreksi") return true;
        return !!(n.indukN && n.indukN.status === "kurang" && n.sifat === "alternatif");
      }
      return true;
    }

    function selesaiKelompok(n) {
      var isi = hasil.p.satuan["g" + n.induk] || [];
      return isi.some(function (x) { return x.dijawab && (x.ada === ADA || x.ada === KOREKSI); });
    }

    function saring() {
      var tampil = {};
      pohon.daftar.forEach(function (n) {
        if (!tapis || tampilMenurut(n)) {
          /* Induknya ikut tampil, supaya butir "b." tidak kehilangan
             konteks grup yang menaunginya. */
          for (var x = n; x; x = x.indukN) tampil[x.id] = true;
        }
      });
      var ada = 0;
      pohon.daftar.forEach(function (n) {
        n.el.hidden = !tampil[n.id];
        if (tampil[n.id]) ada++;
      });
      if (kosong) kosong.hidden = ada > 0;
    }

    function lompat(el) {
      if (!el) return;
      el.hidden = false;
      el.scrollIntoView({ block: "center", behavior: "smooth" });
      el.classList.remove("sorot");
      void el.offsetWidth;                        /* ulang animasinya */
      el.classList.add("sorot");
      var r = el.querySelector('input[type="radio"]:checked') ||
              el.querySelector('input[type="radio"]');
      if (r) r.focus({ preventScroll: true });
    }

    function berikutnyaBelum(dari) {
      var mulai = dari ? pohon.daftar.indexOf(dari) + 1 : 0;
      var urut = pohon.daftar.slice(mulai).concat(pohon.daftar.slice(0, mulai));
      for (var i = 0; i < urut.length; i++) {
        var n = urut[i];
        if (bisaCentang(n) && !n.dijawab && n !== dari &&
            !(n.sifat === "alternatif" && selesaiKelompok(n))) return n;
      }
      return null;
    }

    akar.addEventListener("change", function (ev) {
      if (ev.target.type === "radio") hitung(true);
    });
    akar.addEventListener("input", function (ev) {
      if (ev.target.closest(".periksa-koreksi")) hitung(false);
    });

    akar.addEventListener("click", function (ev) {
      var t = ev.target.closest("[data-tapis]");
      if (t) {
        tapis = t.dataset.tapis;
        akar.querySelectorAll("[data-tapis]").forEach(function (b) {
          var ya = b.dataset.tapis === tapis;
          b.classList.toggle("aktif", ya);
          b.setAttribute("aria-pressed", ya ? "true" : "false");
        });
        saring();
        return;
      }
      if (ev.target.closest("[data-ke-belum]")) {
        var kini = document.activeElement && document.activeElement.closest &&
                   document.activeElement.closest(".periksa-baris");
        var dari = kini && pohon.daftar.filter(function (n) { return n.el === kini; })[0];
        var n = berikutnyaBelum(dari);
        if (n) lompat(n.el);
        return;
      }
      var a = ev.target.closest("[data-lompat]");
      if (a) {
        ev.preventDefault();                      /* jangan ganggu #hash milik tab */
        var el = document.getElementById("butir-" + a.dataset.lompat);
        if (el) {
          var panel = el.closest(".panel");
          var tab = panel && document.getElementById("t-" + panel.id);
          if (tab && !panel.classList.contains("aktif")) tab.click();
          if (el.hidden) { tapis = ""; akar.querySelector('[data-tapis=""]').click(); }
          lompat(el);
        }
      }
    });

    /* 1 / 2 / 3 saat fokus di salah satu pilihan: Ada / Perlu koreksi / Tidak
       Ada. Sesudah Ada atau Tidak Ada kursor pindah ke butir berikutnya yang
       belum; sesudah Perlu koreksi kursor masuk ke kotak catatannya. */
    var daftarEl = akar.querySelector(".periksa");
    if (akar.closest(".fokus") && daftarEl) daftarEl.classList.add("pintas-tampil");
    akar.addEventListener("keydown", function (ev) {
      var r = ev.target;
      if (r.type !== "radio" || ev.ctrlKey || ev.metaKey || ev.altKey) return;
      var nilaiKunci = { "1": ADA, "2": KOREKSI, "3": 0 }[ev.key];
      if (nilaiKunci === undefined) return;
      ev.preventDefault();
      var baris = r.closest(".periksa-baris");
      var pilih = baris.querySelector('input[type="radio"][value="' + nilaiKunci + '"]');
      if (!pilih || pilih.disabled) return;
      pilih.checked = true;
      pilih.dispatchEvent(new Event("change", { bubbles: true }));
      if (nilaiKunci === KOREKSI) {
        var c = baris.querySelector(".periksa-koreksi input");
        if (c) c.focus();
        return;
      }
      var kini = pohon.daftar.filter(function (n) { return n.el === baris; })[0];
      var n = berikutnyaBelum(kini);
      if (n) lompat(n.el); else pilih.focus();
    });

    /* Enter di kotak catatan koreksi: lanjut ke butir berikutnya, bukan
       mengirim formulir tanpa sengaja. */
    akar.addEventListener("keydown", function (ev) {
      if (ev.key !== "Enter" || !ev.target.closest(".periksa-koreksi")) return;
      if (ev.target.list && ev.target.value === "") return;   /* biar datalist */
      ev.preventDefault();
      var baris = ev.target.closest(".periksa-baris");
      var kini = pohon.daftar.filter(function (n) { return n.el === baris; })[0];
      var n = berikutnyaBelum(kini);
      if (n) lompat(n.el);
    });

    hitung(false);
  }

  /* ------------- banyak surat dalam satu butir ------------- */
  /* Butir `jamak` (mis. Akta pemindahan hak, Surat bukti perolehan lainnya)
     menampilkan sederet kotak bernama sama. "+ Tambah surat" menyalin baris
     dari <template>; mengetik di kotak yang pilihannya belum dicentang
     langsung mencentang Ada — surat yang namanya diketik jelas dibawa. */
  function nomoriSurat(wadah) {
    wadah.querySelectorAll(":scope > .surat-baris").forEach(function (b, i) {
      b.querySelector(".surat-no").textContent = (i + 1) + ".";
      b.querySelector("input").setAttribute("aria-label", "Surat ke-" + (i + 1));
    });
    var t = wadah.querySelector("[data-tambah-surat]");
    if (t) t.textContent = wadah.querySelector(":scope > .surat-baris")
      ? "+ Tambah surat" : "+ Rincian surat";
  }

  function tambahSurat(wadah) {
    var baru = wadah.querySelector("template").content.firstElementChild.cloneNode(true);
    wadah.insertBefore(baru, wadah.querySelector("template"));
    nomoriSurat(wadah);
    baru.querySelector("input").focus();
  }

  function pasangSurat() {
    document.addEventListener("click", function (ev) {
      var t = ev.target.closest("[data-tambah-surat]");
      if (t) { tambahSurat(t.closest("[data-surat]")); return; }
      var h = ev.target.closest("[data-hapus-surat]");
      if (!h) return;
      var wadah = h.closest("[data-surat]");
      var baris = h.closest(".surat-baris");
      var lain = baris.nextElementSibling && baris.nextElementSibling.matches(".surat-baris")
        ? baris.nextElementSibling : baris.previousElementSibling;
      baris.remove();
      nomoriSurat(wadah);
      var f = lain && lain.querySelector && lain.querySelector("input");
      (f || wadah.querySelector("[data-tambah-surat]")).focus();
      wadah.dispatchEvent(new Event("input", { bubbles: true }));
    });

    document.addEventListener("input", function (ev) {
      var kotak = ev.target;
      if (!kotak.matches || !kotak.matches(".surat-baris input, .periksa-isian")) return;
      if (!kotak.value.trim()) return;
      var baris = kotak.closest(".periksa-baris");
      if (!baris || baris.querySelector('input[type="radio"]:checked')) return;
      var ada = baris.querySelector('input[type="radio"][value="1"]');
      if (ada && !ada.disabled) {
        ada.checked = true;
        ada.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });

    /* Enter di kotak surat tidak boleh mengirim formulir: pada butir jamak
       Enter membuka kotak surat berikutnya, selebihnya diabaikan. */
    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "Enter" || !ev.target.matches) return;
      if (!ev.target.matches(".surat-baris input, .periksa-isian")) return;
      ev.preventDefault();
      var wadah = ev.target.closest("[data-surat]");
      if (wadah && ev.target.value.trim()) tambahSurat(wadah);
    });
  }

  /* ------------- susun formulir kelengkapan ------------- */
  /* Tombol panah dan formulir di tiap baris sudah cukup tanpa JavaScript.
     Di sini hanya: seret-lepas (dikirim ke rute geser yang sama dengan
     sasaran & posisi, lalu halaman dimuat ulang pada butir yang dipindah),
     saran bunyi butir, dan sorotan baris yang baru disimpan. */
  function pasangSusun() {
    var daftar = document.querySelector("[data-susun]");
    document.addEventListener("change", function (ev) {
      var s = ev.target.closest && ev.target.closest("[data-salin-ke]");
      if (!s || !s.value) return;
      var tujuan = document.getElementById(s.dataset.salinKe);
      if (tujuan) { tujuan.value = s.value; tujuan.focus(); }
      s.value = "";
    });
    /* Ubah / Batal: buka-tutup panel sunting di tempat, tanpa memuat ulang. */
    document.addEventListener("click", function (ev) {
      var t = ev.target.closest("[data-buka-sunting]");
      if (!t) return;
      var panel = document.getElementById(t.dataset.bukaSunting);
      if (!panel) return;
      ev.preventDefault();
      panel.hidden = !panel.hidden;
      var ubah = panel.parentNode.querySelector('.susun-aksi [data-buka-sunting]');
      if (ubah) {
        ubah.classList.toggle("aktif", !panel.hidden);
        ubah.setAttribute("aria-expanded", panel.hidden ? "false" : "true");
      }
      if (!panel.hidden) {
        var isian = panel.querySelector("textarea");
        if (isian) isian.focus();
      } else if (ubah) ubah.focus();
    });
    document.addEventListener("click", function (ev) {
      var a = ev.target.closest("[data-fokus]");
      if (!a) return;
      var el = document.getElementById(a.dataset.fokus);
      if (el) setTimeout(function () { el.focus(); }, 50);
    });
    if (location.hash && /^#s-\d+$/.test(location.hash)) {
      var b = document.querySelector(location.hash);
      if (b) { b.classList.add("sorot"); b.scrollIntoView({ block: "center" }); }
    }
    if (!daftar) return;

    var csrf = document.querySelector('input[name="_csrf"]');
    var seret = null;

    function posisi(ev, li) {
      var r = li.getBoundingClientRect();
      var y = (ev.clientY - r.top) / r.height;
      if (li.dataset.judul === "1" && y > 0.3 && y < 0.7) return "dalam";
      return y < 0.5 ? "sebelum" : "sesudah";
    }
    function bersihkan() {
      daftar.querySelectorAll(".tujuan-sebelum,.tujuan-sesudah,.tujuan-dalam")
        .forEach(function (x) {
          x.classList.remove("tujuan-sebelum", "tujuan-sesudah", "tujuan-dalam");
        });
    }

    daftar.querySelectorAll(".susun-baris[data-id]").forEach(function (li) {
      var pegang = li.querySelector(".susun-pegang");
      if (!pegang) return;
      /* Hanya pegangannya yang menyeret — teks dan isian tetap bisa diblok. */
      pegang.addEventListener("mousedown", function () { li.draggable = true; });
      li.addEventListener("dragstart", function (ev) {
        seret = li;
        li.classList.add("diseret");
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", li.dataset.id);
      });
      li.addEventListener("dragend", function () {
        li.draggable = false;
        li.classList.remove("diseret");
        bersihkan();
      });
    });

    daftar.addEventListener("dragover", function (ev) {
      var li = ev.target.closest(".susun-baris[data-id]");
      if (!seret || !li || li === seret) return;
      ev.preventDefault();
      bersihkan();
      li.classList.add("tujuan-" + posisi(ev, li));
    });
    daftar.addEventListener("dragleave", function (ev) {
      if (!daftar.contains(ev.relatedTarget)) bersihkan();
    });
    daftar.addEventListener("drop", function (ev) {
      var li = ev.target.closest(".susun-baris[data-id]");
      if (!seret || !li || li === seret) return;
      ev.preventDefault();
      var pos = posisi(ev, li), id = seret.dataset.id;
      bersihkan();
      var data = new URLSearchParams();
      data.set("sasaran", li.dataset.id);
      data.set("posisi", pos);
      if (csrf) data.set("_csrf", csrf.value);
      daftar.classList.add("sibuk");
      fetch(daftar.dataset.susun + id + "/geser", {
        method: "POST", body: data, credentials: "same-origin",
        headers: { "X-Diam": "1" }
      }).then(function (r) {
        if (r.ok) { location.hash = "s-" + id; location.reload(); return; }
        return r.text().then(function (t) { throw new Error(t || r.status); });
      }).catch(function (galat) {
        daftar.classList.remove("sibuk");
        var p = document.createElement("div");
        p.className = "pesan galat";
        p.textContent = "Gagal memindah butir: " + galat.message;
        daftar.parentNode.insertBefore(p, daftar);
      });
    });
  }

  /* ------------- peringatan perubahan belum tersimpan ------------- */
  /* Pada formulir bertanda data-jaga-ubah: meninggalkan halaman sesudah
     mengubah sesuatu memunculkan pertanyaan bawaan peramban. Menyimpan
     (mengirim formulirnya) tentu tidak ditanya. */
  function pasangJagaUbah() {
    var form = document.querySelector("form[data-jaga-ubah]");
    if (!form) return;
    var ubah = false;
    var tandai = function () { ubah = true; };
    form.addEventListener("change", tandai);
    form.addEventListener("input", tandai);
    form.addEventListener("submit", function () { ubah = false; });
    window.addEventListener("beforeunload", function (ev) {
      if (!ubah) return;
      ev.preventDefault();
      ev.returnValue = "";
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    pasangMenu();
    pasangTab();
    pasangLangkah();
    pasangBarisDinamis();
    pasangWilayah();
    pasangLuas();
    pasangSaring();
    pasangSaringanServer();
    pasangSimpanPintas();
    pasangKonfirmasi();
    pasangLipat();
    pasangSaringLipat();
    pasangPratinjauFoto();
    pasangRincianBaku();
    pasangCetak();
    pasangPeriksa();
    pasangSurat();
    pasangSusun();
    pasangJagaUbah();
  });
})();
